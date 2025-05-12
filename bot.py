import requests
import json
import logging
import secrets
import asyncio
import os
from eth_account import Account
from eth_account.messages import encode_defunct
from colorama import Fore, Style, init
from datetime import datetime
import pytz
from aiohttp import ClientSession, ClientTimeout
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
import time
import random

# Initialize colorama
init(autoreset=True)

# Set timezone
wib = pytz.timezone('Asia/Jakarta')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    datefmt='[%Y-%m-%d %H:%M:%S]'
)
logger = logging.getLogger("XOSWalletClient")

class XOSWalletClient:
    def __init__(self) -> None:
        # Configuration
        self.PROJECT_ID = "7f8bd096752366cf84c52aa43f99504b"
        self.BASE_URL = "https://rpc.walletconnect.org/v1"
        self.WEB3MODAL_URL = "https://api.web3modal.org"
        self.X_INK_API = "https://api.x.ink/v1"
        self.CHAIN_ID = "eip155:42161"
        
        # Browser headers
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://x.ink",
            "Referer": "https://x.ink/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": FakeUserAgent().random
        }
        
        # Proxy settings
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}

    def welcome(self):
        banner = """
╔══════════════════════════════════════════════╗
║        🔐 XOS Wallet Client                  ║
║     Login & Claim with your EVM wallet       ║
╚══════════════════════════════════════════════╝
"""
        print(f"{Fore.CYAN + Style.BRIGHT}{banner}{Style.RESET_ALL}")

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def log(self, message):
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}{message}",
            flush=True
        )

    def format_seconds(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

    # Wallet login functions
    def get_wallets(self):
        """Fetch wallet data from the WalletConnect API"""
        params = {
            "projectId": self.PROJECT_ID,
            "st": "appkit",
            "sv": "html-ethers-1.6.8",
            "page": 1,
            "chains": self.CHAIN_ID,
            "entries": 4
        }
        headers = {
            "referer": "https://x.ink/",
            "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        }
        try:
            response = requests.get(f"{self.WEB3MODAL_URL}/getWallets", params=params, headers=headers)
            response.raise_for_status()
            self.log(f"{Fore.GREEN + Style.BRIGHT}Successfully fetched wallet data.{Style.RESET_ALL}")
            return response.json()
        except requests.RequestException as e:
            self.log(f"{Fore.RED + Style.BRIGHT}Failed to fetch wallet data: {e}{Style.RESET_ALL}")
            return None

    def get_identity(self, wallet_address, client_id, max_retries=3, initial_delay=5):
        """Get identity for a wallet address with retry logic"""
        params = {
            "projectId": self.PROJECT_ID,
            "sender": wallet_address,
            "apiVersion": "2"
        }
        headers = {
            "accept": "*/*",
            "origin": "https://x.ink",
            "referer": "https://x.ink/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        }
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = initial_delay * (2 ** (attempt - 1))
                    self.log(f"{Fore.YELLOW + Style.BRIGHT}Waiting {delay} seconds before retry...{Style.RESET_ALL}")
                    time.sleep(delay)
                
                response = requests.get(
                    f"{self.BASE_URL}/profile/reverse/{wallet_address}",
                    params=params,
                    headers=headers
                )
                
                if response.status_code == 429:
                    self.log(f"{Fore.YELLOW + Style.BRIGHT}Rate limit hit. Attempt {attempt + 1}/{max_retries}{Style.RESET_ALL}")
                    continue
                    
                response.raise_for_status()
                self.log(f"{Fore.GREEN + Style.BRIGHT}Successfully fetched identity data.{Style.RESET_ALL}")
                
                # Return empty dict if response is empty array
                data = response.json()
                if data == []:
                    return {}
                return data
                
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    self.log(f"{Fore.RED + Style.BRIGHT}Failed to fetch identity data after {max_retries} attempts: {e}{Style.RESET_ALL}")
                    return None
                self.log(f"{Fore.YELLOW + Style.BRIGHT}Attempt {attempt + 1} failed: {e}{Style.RESET_ALL}")

    def get_sign_message(self, wallet_address, max_retries=3, initial_delay=5):
        """Get message that needs to be signed with exponential backoff"""
        params = {
            "walletAddress": wallet_address
        }
        headers = {
            "accept": "application/json, text/plain, */*",
            "origin": "https://x.ink",
            "referer": "https://x.ink/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        }
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = initial_delay * (2 ** (attempt - 1))
                    self.log(f"{Fore.YELLOW + Style.BRIGHT}Waiting {delay} seconds before retry...{Style.RESET_ALL}")
                    time.sleep(delay)
                
                response = requests.get(f"{self.X_INK_API}/get-sign-message2", params=params, headers=headers)
                
                if response.status_code == 429:
                    self.log(f"{Fore.YELLOW + Style.BRIGHT}Rate limit hit. Attempt {attempt + 1}/{max_retries}{Style.RESET_ALL}")
                    continue
                    
                response.raise_for_status()
                self.log(f"{Fore.GREEN + Style.BRIGHT}Successfully fetched sign message.{Style.RESET_ALL}")
                return response.json()
                
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    self.log(f"{Fore.RED + Style.BRIGHT}Failed to fetch sign message after {max_retries} attempts: {e}{Style.RESET_ALL}")
                    return None
                self.log(f"{Fore.YELLOW + Style.BRIGHT}Attempt {attempt + 1} failed: {e}{Style.RESET_ALL}")

    def verify_signature(self, wallet_address, sign_message, signature):
        """Verify the signature with the server"""
        url = f"{self.X_INK_API}/verify-signature2"
        headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "origin": "https://x.ink",
            "referer": "https://x.ink/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        }
        payload = {
            "walletAddress": wallet_address,
            "signMessage": sign_message,
            "signature": signature if signature.startswith("0x") else f"0x{signature}",
            "referrer": "7JPBUS"  # Added referrer as per API payload
        }
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            self.log(f"{Fore.GREEN + Style.BRIGHT}Signature verification successful!{Style.RESET_ALL}")
            return response.json()
        except requests.RequestException as e:
            self.log(f"{Fore.RED + Style.BRIGHT}Signature verification failed: {e}{Style.RESET_ALL}")
            return None

    def save_to_account_file(self, wallet_address, private_key, token=None):
        """Save successful login credentials to account.txt"""
        try:
            with open("account.txt", "a") as f:
                f.write(f"Address: {wallet_address}\n")
                f.write(f"Private Key: {private_key}\n")
                # Save token only if specified by caller
                f.write("=" * 50 + "\n")
            self.log(f"{Fore.GREEN + Style.BRIGHT}Credentials saved to account.txt{Style.RESET_ALL}")
            return True
        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}Failed to save credentials: {e}{Style.RESET_ALL}")
            return False

    def login_with_private_key(self, private_key):
        """Login to XOS using a private key"""
        try:
            # Check if private key is valid
            if not private_key.startswith("0x"):
                private_key = "0x" + private_key
                
            # Create account from private key
            account = Account.from_key(private_key)
            wallet_address = account.address
            self.log(f"{Fore.CYAN + Style.BRIGHT}Using wallet: {Fore.WHITE + Style.BRIGHT}{wallet_address}{Style.RESET_ALL}")
            
            # Get wallets
            wallets = self.get_wallets()
            if not wallets:
                self.log(f"{Fore.RED + Style.BRIGHT}Failed to connect to XOS. Please try again later.{Style.RESET_ALL}")
                return None
                
            # Generate client ID (random unique identifier)
            client_id = f"did:key:z6Mk{secrets.token_hex(32)}"
            
            # Get identity
            identity = self.get_identity(wallet_address, client_id)
            if identity is None:  # Only return None if there was an error
                self.log(f"{Fore.RED + Style.BRIGHT}Failed to fetch identity. Please try again later.{Style.RESET_ALL}")
                return None
                
            # Get sign message
            sign_message_response = self.get_sign_message(wallet_address)
            if not sign_message_response:
                self.log(f"{Fore.RED + Style.BRIGHT}Failed to get sign message. Please try again later.{Style.RESET_ALL}")
                return None
                
            sign_message = sign_message_response.get("message")
            if not sign_message:
                self.log(f"{Fore.RED + Style.BRIGHT}Invalid sign message received.{Style.RESET_ALL}")
                return None
                
            self.log(f"{Fore.GREEN + Style.BRIGHT}Sign message received successfully.{Style.RESET_ALL}")
            
            # Sign the message
            try:
                message = encode_defunct(text=sign_message)
                signed_message = Account.sign_message(message, private_key=private_key)
                signature = signed_message.signature.hex()
                self.log(f"{Fore.GREEN + Style.BRIGHT}Signature generated successfully.{Style.RESET_ALL}")
                
                # Verify locally
                recovered_address = Account.recover_message(message, signature=signature)
                if recovered_address.lower() != wallet_address.lower():
                    self.log(f"{Fore.RED + Style.BRIGHT}Local signature verification failed: address mismatch.{Style.RESET_ALL}")
                    return None
                    
                self.log(f"{Fore.GREEN + Style.BRIGHT}Local signature verification successful.{Style.RESET_ALL}")
            except Exception as e:
                self.log(f"{Fore.RED + Style.BRIGHT}Failed to sign message: {e}{Style.RESET_ALL}")
                return None
                
            # Verify signature with server
            verification = self.verify_signature(wallet_address, sign_message, signature)
            if verification:
                # Extract token if available
                token = verification.get("token", None) if isinstance(verification, dict) else verification
                
                # Save credentials to account.txt
                saved = self.save_to_account_file(wallet_address, private_key)
                if saved:
                    self.log(f"{Fore.GREEN + Style.BRIGHT}Login Success! Credentials saved to account.txt{Style.RESET_ALL}")
                    
                    separator = "=" * 25
                    self.log(f"{Fore.CYAN + Style.BRIGHT}{separator} ACCOUNT INFO {separator}{Style.RESET_ALL}")
                    return token
            else:
                self.log(f"{Fore.RED + Style.BRIGHT}Server signature verification failed.{Style.RESET_ALL}")
                return None
                
        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}Login failed: {e}{Style.RESET_ALL}")
            return None

    # XOS functions for account interaction after login
    async def user_data(self, token, proxy=None, retries=3):
        """Get user data with the authentication token"""
        url = "https://api.x.ink/v1/me"
        headers = {
            **self.headers,
            "authorization": f"Bearer {token}"
        }
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy) if proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.get(url=url, headers=headers) as response:
                        response.raise_for_status()
                        result = await response.json()
                        if isinstance(result, dict) and 'data' in result:
                            return result['data']
                        return result
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                    continue
                return None
            
    async def claim_checkin(self, token, proxy=None, retries=3):
        """Claim daily check-in rewards"""
        url = "https://api.x.ink/v1/check-in"
        headers = {
            **self.headers,
            "authorization": f"Bearer {token}",
            "Content-Length": "2",
            "Content-Type": "application/json"
        }
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy) if proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, json={}) as response:
                        response.raise_for_status()
                        return await response.json()
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                    continue

                self.log(f"{Fore.RED + Style.BRIGHT}Failed to check-in: {e}{Style.RESET_ALL}")
                return None
            
    async def perform_draw(self, token, proxy=None, retries=3):
        """Perform a draw to earn rewards"""
        url = "https://api.x.ink/v1/draw"
        headers = {
            **self.headers,
            "authorization": f"Bearer {token}",
            "Content-Length": "2",
            "Content-Type": "application/json"
        }
        for attempt in range(retries):
            connector = ProxyConnector.from_url(proxy) if proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url=url, headers=headers, json={}) as response:
                        response.raise_for_status()
                        return await response.json()
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                    continue

                self.log(f"{Fore.RED + Style.BRIGHT}Failed to perform draw: {e}{Style.RESET_ALL}")
                return None

    async def process_account(self, token, proxy=None):
        """Process an account with the given token"""
        # Validate token status
        self.log(f"{Fore.CYAN + Style.BRIGHT}Validating token...{Style.RESET_ALL}")
        user = await self.user_data(token, proxy)
        
        if not user:
            self.log(f"{Fore.RED + Style.BRIGHT}Token invalid or expired{Style.RESET_ALL}")
            return False
            
        self.log(f"{Fore.GREEN + Style.BRIGHT}Token valid!{Style.RESET_ALL}")
        
        # Get and display user info
        balance = user.get("points", 0)
        current_draw = user.get("currentDraws", 0)
        wallet_address = user.get("walletAddress", "N/A")
        
        self.log(f"{Fore.CYAN + Style.BRIGHT}Wallet  :{Style.RESET_ALL} {Fore.WHITE + Style.BRIGHT}{wallet_address}{Style.RESET_ALL}")
        self.log(f"{Fore.CYAN + Style.BRIGHT}Balance :{Style.RESET_ALL} {Fore.WHITE + Style.BRIGHT}{balance} PTS{Style.RESET_ALL}")

        # Attempt to claim daily check-in
        claim = await self.claim_checkin(token, proxy)
        if claim and claim.get("success", False):
            days = claim['check_in_count']
            reward = claim['pointsEarned']
            self.log(
                f"{Fore.CYAN + Style.BRIGHT}Check-In:{Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT} Day {days} {Style.RESET_ALL}"
                f"{Fore.GREEN + Style.BRIGHT}Is Claimed{Style.RESET_ALL}"
                f"{Fore.MAGENTA + Style.BRIGHT} - {Style.RESET_ALL}"
                f"{Fore.CYAN + Style.BRIGHT}Reward{Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT} {reward} PTS{Style.RESET_ALL}"
            )
        elif claim:
            if claim.get("error") == "Already checked in today":
                self.log(
                    f"{Fore.CYAN + Style.BRIGHT}Check-In:{Style.RESET_ALL}"
                    f"{Fore.YELLOW + Style.BRIGHT} Already Claimed Today{Style.RESET_ALL}"
                )
            elif claim.get("error") == "Please follow Twitter or join Discord first":
                self.log(
                    f"{Fore.CYAN + Style.BRIGHT}Check-In:{Style.RESET_ALL}"
                    f"{Fore.YELLOW + Style.BRIGHT} Not Eligible, {Style.RESET_ALL}"
                    f"{Fore.WHITE + Style.BRIGHT}Connect Your X or Discord Account First{Style.RESET_ALL}"
                )
            else:
                self.log(
                    f"{Fore.CYAN + Style.BRIGHT}Check-In:{Style.RESET_ALL}"
                    f"{Fore.RED + Style.BRIGHT} Error: {claim.get('error', 'Unknown Error')}{Style.RESET_ALL}"
                )
        else:
            self.log(
                f"{Fore.CYAN + Style.BRIGHT}Check-In:{Style.RESET_ALL}"
                f"{Fore.RED + Style.BRIGHT} Failed to claim{Style.RESET_ALL}"
            )

        # Process available draws
        if current_draw > 0:
            self.log(
                f"{Fore.CYAN + Style.BRIGHT}Draw    :{Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT} {current_draw} {Style.RESET_ALL}"
                f"{Fore.GREEN + Style.BRIGHT}Available{Style.RESET_ALL}"
            )

            count = 0
            while current_draw > 0:
                count += 1

                draw = await self.perform_draw(token, proxy)
                if draw and draw.get("message") == "Draw successful":
                    reward = draw['pointsEarned']
                    self.log(
                        f"{Fore.MAGENTA + Style.BRIGHT}    >{Style.RESET_ALL}"
                        f"{Fore.WHITE + Style.BRIGHT} {count} {Style.RESET_ALL}"
                        f"{Fore.GREEN + Style.BRIGHT}Success{Style.RESET_ALL}"
                        f"{Fore.MAGENTA + Style.BRIGHT} - {Style.RESET_ALL}"
                        f"{Fore.CYAN + Style.BRIGHT}Reward{Style.RESET_ALL}"
                        f"{Fore.WHITE + Style.BRIGHT} {reward} PTS{Style.RESET_ALL}"
                    )
                    current_draw -= 1
                else:
                    self.log(
                        f"{Fore.MAGENTA + Style.BRIGHT}    >{Style.RESET_ALL}"
                        f"{Fore.WHITE + Style.BRIGHT} {count} {Style.RESET_ALL}"
                        f"{Fore.RED + Style.BRIGHT}Failed{Style.RESET_ALL}"
                    )
                    break
        else:
            self.log(
                f"{Fore.CYAN + Style.BRIGHT}Draw    :{Style.RESET_ALL}"
                f"{Fore.YELLOW + Style.BRIGHT} No Available Draws{Style.RESET_ALL}"
            )
            
        return True

async def run_with_private_key(private_key):
    """Run the XOS client with a single private key"""
    client = XOSWalletClient()
    
    # Login with private key to get token
    token = client.login_with_private_key(private_key)
    
    if token:
        # Process the account with the obtained token
        result = await client.process_account(token)
        return result
    else:
        client.log(f"{Fore.RED + Style.BRIGHT}Login failed. Unable to process account.{Style.RESET_ALL}")
        return False

async def process_multiple_keys(keys):
    """Process multiple private keys with increased delay"""
    client = XOSWalletClient()
    client.welcome()  # Show welcome banner only once at the start
    
    total_accounts = len(keys)
    successful = 0
    failed = 0
    total_points = 0
    
    print(f"\n{Fore.CYAN + Style.BRIGHT}{'=' * 60}[ Starting Process ]{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.WHITE + Style.BRIGHT}Total Accounts to Process: {total_accounts}{Style.RESET_ALL}\n")
    
    for index, private_key in enumerate(keys, 1):
        print(f"\n{Fore.CYAN + Style.BRIGHT}{'=' * 60}[ Account {index}/{total_accounts} ]{'=' * 60}{Style.RESET_ALL}\n")
        
        try:
            result = await run_with_private_key(private_key)
            if result:
                successful += 1
                # Try to get points earned if available
                try:
                    user_data = await client.user_data(result)
                    if user_data:
                        points = user_data.get("points", 0)
                        total_points += points
                except:
                    pass
            else:
                failed += 1
        except Exception as e:
            client.log(f"{Fore.RED + Style.BRIGHT}Error processing account {index}: {e}{Style.RESET_ALL}")
            failed += 1
        
        # Add longer delay between accounts (15-30 seconds)
        if index < total_accounts:
            delay = random.randint(15, 30)
            client.log(f"{Fore.YELLOW + Style.BRIGHT}Waiting {delay} seconds before processing next account.{Style.RESET_ALL}")
            await asyncio.sleep(delay)
    
    # Print detailed summary
    print(f"\n{Fore.CYAN + Style.BRIGHT}{'=' * 60}[ Final Summary ]{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN + Style.BRIGHT}✓ Successfully Processed: {successful} accounts{Style.RESET_ALL}")
    print(f"{Fore.RED + Style.BRIGHT}✗ Failed to Process: {failed} accounts{Style.RESET_ALL}")
    print(f"{Fore.YELLOW + Style.BRIGHT}📊 Success Rate: {(successful/total_accounts)*100:.1f}%{Style.RESET_ALL}")
    if total_points > 0:
        print(f"{Fore.MAGENTA + Style.BRIGHT}💰 Total Points Earned: {total_points} PTS{Style.RESET_ALL}")
    print(f"\n{Fore.CYAN + Style.BRIGHT}{'=' * 60}[ Process Completed ]{'=' * 60}{Style.RESET_ALL}")

def extract_private_keys_from_account_file():
    """Extract private keys from account.txt file"""
    keys = []
    
    try:
        if not os.path.exists("account.txt"):
            return keys
            
        with open("account.txt", "r") as file:
            lines = file.readlines()
            
        for line in lines:
            # Extract private keys - look for lines with "Private Key: " prefix
            if line.strip().startswith("Private Key:"):
                # Extract the key part after "Private Key: "
                key = line.strip()[len("Private Key: "):]
                # Skip if already in the list to avoid duplicates
                if key not in keys:
                    keys.append(key)
                    
        return keys
    except Exception as e:
        print(f"{Fore.RED + Style.BRIGHT}Error reading account.txt: {str(e)}{Style.RESET_ALL}")
        return []

def main():
    """Main function to handle the XOS wallet client"""
    client = XOSWalletClient()
    client.welcome()
    
    try:
        import sys
        import os
        
        # Check if argument is provided to use account.txt
        if len(sys.argv) > 1 and sys.argv[1] == "--account":
            # Process keys from account.txt file
            keys = extract_private_keys_from_account_file()
            
            if keys:
                client.log(f"{Fore.GREEN + Style.BRIGHT}Loading {len(keys)} private keys from account.txt{Style.RESET_ALL}")
                asyncio.run(process_multiple_keys(keys))
            else:
                client.log(f"{Fore.YELLOW + Style.BRIGHT}No private keys found in account.txt{Style.RESET_ALL}")
            return
        
        # Check if argument is provided to use keys.txt
        elif len(sys.argv) > 1 and sys.argv[1] == "--file":
            # Process keys from keys.txt file
            if os.path.exists("keys.txt"):
                with open("keys.txt", "r") as file:
                    keys = [line.strip() for line in file if line.strip()]
                
                if keys:
                    client.log(f"{Fore.GREEN + Style.BRIGHT}Loading {len(keys)} keys from keys.txt{Style.RESET_ALL}")
                    asyncio.run(process_multiple_keys(keys))
                else:
                    client.log(f"{Fore.YELLOW + Style.BRIGHT}No keys found in keys.txt{Style.RESET_ALL}")
            else:
                client.log(f"{Fore.RED + Style.BRIGHT}File keys.txt not found. Please create it and add your private keys (one per line).{Style.RESET_ALL}")
            return
                
        # Check if a single private key was provided as argument
        elif len(sys.argv) > 1:
            private_key = sys.argv[1]
            client.log(f"{Fore.GREEN + Style.BRIGHT}Using provided private key: {private_key[:5]}...{private_key[-5:]}{Style.RESET_ALL}")
            asyncio.run(run_with_private_key(private_key))
            return
            
        # No arguments - show options
        print(f"\n{Fore.YELLOW + Style.BRIGHT}Choose an option:{Style.RESET_ALL}")
        print(f"{Fore.WHITE + Style.BRIGHT}1. Process a single private key{Style.RESET_ALL}")
        print(f"{Fore.WHITE + Style.BRIGHT}2. Process multiple keys from keys.txt{Style.RESET_ALL}")
        print(f"{Fore.WHITE + Style.BRIGHT}3. Process keys from account.txt{Style.RESET_ALL}")
        
        choice = input(f"\n{Fore.CYAN + Style.BRIGHT}Enter your choice (1/2/3): {Style.RESET_ALL}")
        
        if choice == "1":
            # Interactive mode for a single key
            print(f"\n{Fore.YELLOW + Style.BRIGHT}Enter your EVM wallet private key to login to XOS{Style.RESET_ALL}")
            print(f"{Fore.WHITE}(Without 0x prefix is also accepted){Style.RESET_ALL}\n")
            
            while True:
                private_key = input(f"{Fore.CYAN + Style.BRIGHT}Enter private key: {Style.RESET_ALL}")
                if not private_key:
                    print(f"{Fore.YELLOW}No private key entered. Please try again.{Style.RESET_ALL}")
                    continue
                    
                # Try to login with the provided private key
                asyncio.run(run_with_private_key(private_key))
                break
                
        elif choice == "2":
            # Process from keys.txt
            if os.path.exists("keys.txt"):
                with open("keys.txt", "r") as file:
                    keys = [line.strip() for line in file if line.strip()]
                
                if keys:
                    client.log(f"{Fore.GREEN + Style.BRIGHT}Loading {len(keys)} keys from keys.txt{Style.RESET_ALL}")
                    asyncio.run(process_multiple_keys(keys))
                else:
                    client.log(f"{Fore.YELLOW + Style.BRIGHT}No keys found in keys.txt{Style.RESET_ALL}")
            else:
                client.log(f"{Fore.RED + Style.BRIGHT}File keys.txt not found. Please create it and add your private keys (one per line).{Style.RESET_ALL}")
                
        elif choice == "3":
            # Process from account.txt
            keys = extract_private_keys_from_account_file()
            
            if keys:
                client.log(f"{Fore.GREEN + Style.BRIGHT}Loading {len(keys)} private keys from account.txt{Style.RESET_ALL}")
                asyncio.run(process_multiple_keys(keys))
            else:
                client.log(f"{Fore.YELLOW + Style.BRIGHT}No private keys found in account.txt{Style.RESET_ALL}")
        else:
            client.log(f"{Fore.RED + Style.BRIGHT}Invalid choice. Please try again.{Style.RESET_ALL}")
                
    except KeyboardInterrupt:
        client.log(f"{Fore.YELLOW + Style.BRIGHT}Process stopped by user.{Style.RESET_ALL}")
    except Exception as e:
        client.log(f"{Fore.RED + Style.BRIGHT}An unexpected error occurred: {e}{Style.RESET_ALL}")
    finally:
        client.log(f"{Fore.GREEN + Style.BRIGHT}Thank you for using XOS Wallet Client!{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
