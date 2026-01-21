import asyncio
import signal
import sys
from typing import List

from plugins.utilities.foundation.logger.logger import Logger
from plugins.utilities.foundation.plugins_manager.plugins_manager import PluginsManager
from plugins.utilities.foundation.settings_manager.settings_manager import SettingsManager

from .di_container import DIContainer

# Shutdown settings are now taken from config/settings.yaml via settings_manager


class Application:
    """Main application class - manages the lifecycle"""
    
    def __init__(self):
        self.logger_instance = Logger()
        self.logger = self.logger_instance.get_logger("application")
        self.is_running = False
        self.plugins_manager = None
        self.settings_manager = None
        self.di_container = None
        self._background_tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        self._shutdown_requested = False
        
        # Register signals IMMEDIATELY after creating logger
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, _):
        """Signal handler for graceful shutdown"""
        if hasattr(self, 'logger') and self.logger:
            self.logger.info(f"Received signal {signum}, starting graceful shutdown...")
        
        # Check if we already received a signal
        if hasattr(self, '_shutdown_requested') and self._shutdown_requested:
            try:
                if hasattr(self, 'logger') and self.logger:
                    self.logger.critical("Received duplicate termination signal, forcing application shutdown!")
                else:
                    print("[SIGNAL] Received duplicate termination signal!")
            except Exception:
                print("[SIGNAL] Duplicate signal, forcing termination!")
            import os
            os._exit(1)
        
        # Set shutdown request flag
        self._shutdown_requested = True
        
        # Simply set the shutdown event
        if self.is_running:
            try:
                if hasattr(self, 'logger') and self.logger:
                    self.logger.info("Setting shutdown event")
                else:
                    print("[SIGNAL] Setting shutdown event")
            except Exception:
                print("[SIGNAL] Setting shutdown event")
            self._shutdown_event.set()
        else:
            try:
                if hasattr(self, 'logger') and self.logger:
                    self.logger.info("Application not started yet, ignoring signal")
                else:
                    print("[SIGNAL] Application not started yet, ignoring signal")
            except Exception:
                print("[SIGNAL] Application not started")
    
    async def startup(self):
        """Asynchronous application startup"""
        self.logger.info("Starting application...")
        self.is_running = True
        
        try:
            # 1. Create plugins_manager via DI container
            self.logger.info("Initializing plugins_manager...")
            self.plugins_manager = PluginsManager(logger=self.logger_instance.get_logger("plugins_manager"))
            
            # 2. Create settings_manager
            self.logger.info("Initializing settings_manager...")
            self.settings_manager = SettingsManager(
                logger=self.logger_instance.get_logger("settings_manager"),
                plugins_manager=self.plugins_manager
            )
            
            # 3. Create DI container with plugins_manager and settings_manager
            self.logger.info("Creating DI container...")
            self.di_container = DIContainer(
                logger=self.logger_instance, 
                plugins_manager=self.plugins_manager,
                settings_manager=self.settings_manager
            )
            
            # 4. Initialize all plugins automatically
            self.logger.info("Initializing all plugins...")
            self.di_container.initialize_all_plugins()
            
            # 5. Start all services in background tasks
            self.logger.info("Starting all services...")
            await self._start_all_services()
            
            self.logger.info("Application started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting application: {e}")
            await self.shutdown()
            sys.exit(1)
    
    async def _start_all_services(self):
        """Start services according to plan from SettingsManager"""
        # Get startup plan from DI container (already built)
        startup_plan = self.di_container.get_startup_plan()
        
        if not startup_plan:
            self.logger.error("DI container failed to get startup plan")
            return
        
        enabled_services = startup_plan.get('enabled_services', [])
        
        if not enabled_services:
            self.logger.info("No enabled services found for startup")
            return
        
        self.logger.info(f"Starting services according to plan: {len(enabled_services)} services")
        
        for service_name in enabled_services:
            try:
                # Get service instance from DI container
                service_instance = self.di_container.get_service(service_name)
                
                if not service_instance:
                    self.logger.error(f"Failed to get service instance {service_name}")
                    continue
                
                # Check if service has run method
                if hasattr(service_instance, 'run'):
                    self.logger.info(f"Starting service: {service_name}")
                    
                    # Create background task
                    task = asyncio.create_task(service_instance.run(), name=service_name)
                    self._background_tasks.append(task)
                    
                else:
                    self.logger.warning(f"Service {service_name} does not have run() method")
                    
            except Exception as e:
                self.logger.error(f"Error starting service {service_name}: {e}")
        
        self.logger.info(f"Started background tasks: {len(self._background_tasks)}")
    
    async def _async_shutdown(self):
        """Asynchronous graceful shutdown"""
        if not self.is_running:
            return
            
        self.logger.info("Starting async application shutdown...")
        self.is_running = False
        self._shutdown_event.set()
        
        try:
            # Get shutdown settings from global settings
            global_settings = self.settings_manager.get_global_settings()
            shutdown_settings = global_settings.get('shutdown', {})
            di_container_timeout = shutdown_settings.get('di_container_timeout', 5.0)
            background_tasks_timeout = shutdown_settings.get('background_tasks_timeout', 2.0)
            
            # Calculate total timeout for logging
            total_shutdown_timeout = di_container_timeout + background_tasks_timeout
            self.logger.info(f"Starting shutdown with total timeout {total_shutdown_timeout} seconds (di_container: {di_container_timeout}s, background_tasks: {background_tasks_timeout}s)...")
            
            # STEP 1: Shutdown all plugins (utilities and services)
            # Plugins stop their internal background tasks (polling, scheduled scenarios, task processors, etc.)
            if self.di_container:
                self.logger.info("Starting DI container shutdown (stopping all plugins)...")
                try:
                    # Create shutdown task with timeout
                    shutdown_task = asyncio.create_task(
                        asyncio.to_thread(self.di_container.shutdown)
                    )
                    await asyncio.wait_for(shutdown_task, timeout=di_container_timeout)
                    self.logger.info("DI container gracefully terminated, all plugins stopped")
                except asyncio.TimeoutError:
                    self.logger.warning("DI container shutdown timeout, forcing termination")
                    shutdown_task.cancel()
                    self.logger.info("DI container forcefully terminated")
                except Exception as e:
                    self.logger.error(f"Error shutting down DI container: {e}")
                    shutdown_task.cancel()
                    self.logger.info("DI container forcefully terminated after error")
            
            # STEP 2: Cancel all application background tasks (service.run() tasks)
            if self._background_tasks:
                self.logger.info(f"Cancelling {len(self._background_tasks)} background tasks...")
                for task in self._background_tasks:
                    if not task.done():
                        task.cancel()
                
                # Wait for all tasks to complete with timeout
                try:
                    # Use asyncio.wait instead of gather for correct timeout handling
                    done, pending = await asyncio.wait(
                        self._background_tasks,
                        timeout=background_tasks_timeout,
                        return_when=asyncio.ALL_COMPLETED
                    )
                    
                    if pending:
                        self.logger.warning(f"Timeout waiting for {len(pending)} background tasks to complete, forcing termination")
                        # Forcefully terminate unfinished tasks
                        for task in pending:
                            task.cancel()
                        self.logger.info("All background tasks forcefully terminated")
                    else:
                        self.logger.info("All background tasks completed gracefully")
                        
                except Exception as e:
                    self.logger.error(f"Error waiting for tasks to complete: {e}")
                    # Forcefully terminate all tasks
                    for task in self._background_tasks:
                        if not task.done():
                            task.cancel()
                    self.logger.info("All background tasks forcefully terminated after error")
            
            self.logger.info("Application gracefully terminated")
            
        except Exception as e:
            self.logger.error(f"Error during async shutdown: {e}")
            # As a last resort, forcefully terminate the process
            self.logger.critical("Critical shutdown error, forcefully terminating process...")
            import os
            os._exit(1)
    
    def shutdown(self):
        """Synchronous shutdown for backward compatibility"""
        if not self.is_running:
            return
            
        self.logger.info("Starting application shutdown...")
        self.is_running = False
        
        try:
            # Cancel all background tasks
            if self._background_tasks:
                self.logger.info(f"Cancelling {len(self._background_tasks)} background tasks...")
                for task in self._background_tasks:
                    if not task.done():
                        task.cancel()
            
            # Shutdown DI container
            if self.di_container:
                self.di_container.shutdown()
            
            self.logger.info("Application gracefully terminated")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    async def run(self):
        """Asynchronous main application loop"""
        await self.startup()
        
        try:
            # Wait for shutdown event or completion of all services
            self.logger.info("Application started, waiting for shutdown event...")
            await self._shutdown_event.wait()
            self.logger.info("Shutdown event received!")
            
        except KeyboardInterrupt:
            self.logger.info("KeyboardInterrupt received")
        finally:
            await self._async_shutdown()
    
    def run_sync(self):
        """Synchronous wrapper for running async application"""
        try:
            asyncio.run(self.run())
        except KeyboardInterrupt:
            self.logger.info("KeyboardInterrupt received, terminating application")
        except SystemExit:
            raise
        except Exception as e:
            self.logger.error(f"Error in run_sync: {e}")
            sys.exit(1) 