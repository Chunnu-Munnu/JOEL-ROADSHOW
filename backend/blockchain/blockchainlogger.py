"""
app/core/blockchain/blockchain_logger.py
Blockchain logger for approved threats
"""
from web3 import Web3
from web3.middleware import geth_poa_middleware
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class BlockchainLogger:
    """Logs approved security events to blockchain"""
    
    def __init__(self, rpc_url: str = "http://127.0.0.1:8545"):
        self.w3 = None
        self.contract = None
        self.account = None
        self.rpc_url = rpc_url
        
        try:
            self.w3 = Web3(Web3.HTTPProvider(rpc_url))
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            if self.w3.is_connected():
                logger.info(f"✅ Connected to blockchain at {rpc_url}")
                
                # Get first account (from Hardhat)
                accounts = self.w3.eth.accounts
                if accounts:
                    self.account = accounts[0]
                    balance = self.w3.eth.get_balance(self.account)
                    logger.info(f"📝 Using account: {self.account}")
                    logger.info(f"💰 Balance: {self.w3.from_wei(balance, 'ether')} ETH")
                    
                    # Try to load contract
                    self._load_contract()
                else:
                    logger.error("No accounts found")
            else:
                logger.error("Failed to connect to blockchain")
                
        except Exception as e:
            logger.error(f"Blockchain init error: {e}")
            logger.warning("System will run without blockchain")
    
    def _load_contract(self):
        """Load deployed contract from artifacts"""
        try:
            # Try to load deployment info
            base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
            deployment_file = base_dir / "blockchain" / "deployment-info.json"
            abi_file = base_dir / "blockchain" / "SecurityLog-ABI.json"
            
            if not deployment_file.exists() or not abi_file.exists():
                logger.warning("Contract not deployed yet. Run: npx hardhat run scripts/deploy.js --network localhost")
                return
            
            with open(deployment_file, 'r') as f:
                deployment = json.load(f)
            
            with open(abi_file, 'r') as f:
                abi = json.load(f)
            
            contract_address = deployment['address']
            
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=abi
            )
            
            logger.info(f"✅ Contract loaded: {contract_address}")
            
        except Exception as e:
            logger.error(f"Contract loading error: {e}")
    
    def log_threat(self, threat_data: dict) -> str:
        """Log approved threat to blockchain"""
        if not self.contract or not self.account:
            logger.debug("Blockchain logging disabled")
            return None
        
        try:
            # Only log HIGH and CRITICAL
            if threat_data['threat_level'] not in ['HIGH', 'CRITICAL']:
                return None
            
            # Prepare data
            event_type = threat_data.get('threat_type', 'unknown')
            severity = threat_data['threat_level']
            description = self._build_description(threat_data)
            location = f"{threat_data['camera_id']}_x{threat_data['position'][0]}_y{threat_data['position'][1]}"
            snapshot_hash = threat_data.get('snapshot_id', '')
            
            # Call smart contract
            logger.info(f"📝 Logging to blockchain: {event_type}")
            
            tx_hash = self.contract.functions.logEvent(
                event_type,
                severity,
                description,
                location,
                snapshot_hash
            ).transact({
                'from': self.account,
                'gas': 3000000
            })
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            logger.info(f"✅ Blockchain TX: {tx_hash.hex()}")
            logger.info(f"⛽ Gas used: {receipt['gasUsed']}")
            
            return tx_hash.hex()
            
        except Exception as e:
            logger.error(f"Blockchain logging error: {e}")
            return None
    
    def _build_description(self, threat: dict) -> str:
        """Build human-readable description"""
        parts = [f"Track #{threat['track_id']}"]
        
        if threat.get('behaviors'):
            parts.append(f"Behaviors: {', '.join(threat['behaviors'])}")
        
        if threat.get('metadata', {}).get('weapon'):
            weapon = threat['metadata']['weapon']
            parts.append(f"Armed with {weapon['type']}")
        
        if threat.get('metadata', {}).get('pose'):
            parts.append(f"Pose: {threat['metadata']['pose']}")
        
        return " | ".join(parts)
    
    def get_recent_events(self, count: int = 10):
        """Get recent blockchain events"""
        if not self.contract:
            return []
        
        try:
            total = self.contract.functions.getEventCount().call()
            
            events = []
            start = max(0, total - count)
            
            for i in range(start, total):
                event = self.contract.functions.getEvent(i).call()
                events.append({
                    'id': event[0],
                    'event_type': event[1],
                    'severity': event[2],
                    'description': event[3],
                    'location': event[4],
                    'snapshot_hash': event[5],
                    'timestamp': datetime.fromtimestamp(event[6]).isoformat(),
                    'is_approved': event[7]
                })
            
            return events
            
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            return []