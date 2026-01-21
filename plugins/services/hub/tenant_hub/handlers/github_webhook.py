"""
GitHub Webhook Handler - handler for GitHub webhooks
Signature validation and push event processing for tenant synchronization
"""

import hashlib
import hmac
import json

from aiohttp import web


class GitHubWebhookHandler:
    """Handler for GitHub webhooks"""
    
    def __init__(self, action_hub, webhook_secret: str, logger):
        self.action_hub = action_hub
        self.webhook_secret = webhook_secret
        self.logger = logger

    async def handle(self, request: web.Request) -> web.Response:
        """GitHub webhook handler"""
        try:
            # Get request body
            payload_body = await request.read()
            
            # Get headers
            signature = request.headers.get('X-Hub-Signature-256', '')
            event_type = request.headers.get('X-GitHub-Event', '')
            
            # Signature validation
            if not self._verify_signature(payload_body, signature):
                self.logger.warning("Invalid GitHub webhook signature")
                return web.Response(
                    status=401,
                    text="Invalid signature"
                )
            
            # Parse JSON payload
            try:
                payload = json.loads(payload_body.decode('utf-8'))
            except json.JSONDecodeError as e:
                self.logger.error(f"Error parsing JSON payload: {e}")
                return web.Response(
                    status=400,
                    text="Invalid JSON"
                )
            
            # Process only push events
            if event_type != 'push':
                self.logger.info(f"Ignoring event type {event_type}")
                return web.Response(
                    status=200,
                    text="Event ignored"
                )
            
            # Extract list of changed files from payload
            all_files = []
            commits = payload.get('commits', [])
            for commit in commits:
                # Collect all changed files from all commits
                all_files.extend(commit.get('added', []))
                all_files.extend(commit.get('modified', []))
                all_files.extend(commit.get('removed', []))
            
            if not all_files:
                self.logger.info("No changed files in push event")
                return web.Response(
                    status=200,
                    text="No file changes"
                )
            
            # Call universal sync method through ActionHub
            # It uses existing logic from smart_sync for parsing
            result = await self.action_hub.execute_action(
                'sync_tenants_from_files',
                {'files': all_files},  # Pass list of file paths
                fire_and_forget=True  # Async, don't wait for completion
            )
            
            if result.get('result') not in ['success', 'partial_success']:
                error_obj = result.get('error', {})
                self.logger.error(
                    f"Error syncing tenants via webhook: "
                    f"{error_obj.get('message', 'Unknown error')}"
                )
            else:
                response_data = result.get('response_data', {})
                synced = response_data.get('synced_tenants', 0)
                total = response_data.get('total_tenants', 0)
                self.logger.info(f"Synced {synced} of {total} tenants via webhook")
            
            return web.Response(
                status=200,
                text="Webhook processed"
            )
            
        except Exception as e:
            self.logger.error(f"Error processing GitHub webhook: {e}")
            return web.Response(
                status=500,
                text="Internal server error"
            )
            
    def _verify_signature(self, payload_body: bytes, signature: str) -> bool:
        """Validate GitHub webhook signature"""
        if not self.webhook_secret:
            return False
        
        if not signature:
            return False
        
        # GitHub sends signature in format "sha256=..."
        if not signature.startswith('sha256='):
            return False
        
        # Extract hash from signature
        received_hash = signature[7:]
        
        # Calculate expected hash
        expected_hash = hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        # Compare securely
        return hmac.compare_digest(received_hash, expected_hash)

