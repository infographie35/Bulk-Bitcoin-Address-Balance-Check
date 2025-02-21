import asyncio
import subprocess
import os
import time
import socket
import datetime
import json
from collections import deque

# File paths
input_file = r'c:\\your_path\\bitcoin_addresses.txt'
positive_balance_file = r'c:\\your_path\\walletwithbalance.txt'
failure_file = r'c:\\your_path\\failure.txt'
potentially_not_checked_file = r'c:\\your_path\\Potentially_not_checked.txt'
electrum_path = r'c:\\your_path\\electrum-4.5.5-portable.exe'

lass TimeEstimator:
    def __init__(self, max_samples=200):
        self.times = deque(maxlen=max_samples)
        self.start_time = time.time()

    def update(self, elapsed_time):
        self.times.append(elapsed_time)

    def estimate_remaining_time(self, remaining_tasks):
        if len(self.times) == 0:
            return None
        avg_time_per_task = sum(self.times) / len(self.times)
        return avg_time_per_task * remaining_tasks


### Connectivity Checks (synchronous helpers)

def is_internet_available() -> bool:
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

def is_electrum_available() -> bool:
    try:
        result = subprocess.run([electrum_path, '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


### Asynchronous Connectivity Monitor

async def monitor_connectivity(connectivity_event: asyncio.Event):
    """
    Checks connectivity and Electrum availability every 2 seconds.
    When both are available, sets the event so workers can proceed.
    If connectivity is restored after an outage, waits 30 seconds before resuming.
    """
    was_down = False
    while True:
        # Run blocking checks in a thread
        internet_ok = await asyncio.to_thread(is_internet_available)
        electrum_ok = await asyncio.to_thread(is_electrum_available)
        if internet_ok and electrum_ok:
            if not connectivity_event.is_set():
                if was_down:
                    print("Internet and Electrum are back online. Resuming in 30 seconds...")
                    for i in range(30, 0, -1):
                        print(f"Resuming in {i} seconds...", end="\r")
                        await asyncio.sleep(1)
                    print("\nResuming tasks...")
                connectivity_event.set()
                was_down = False
        else:
            if connectivity_event.is_set():
                print("Connectivity lost. Pausing new tasks...")
            connectivity_event.clear()
            was_down = True
        await asyncio.sleep(2)

async def initial_safeguard_check_async():
    """
    Before starting processing, wait until connectivity and Electrum are available.
    """
    while not (await asyncio.to_thread(is_internet_available) and await asyncio.to_thread(is_electrum_available)):
        print("Waiting for internet connection and Electrum availability...")
        await asyncio.sleep(2)


### Utility Functions (remain synchronous)

def is_valid_bitcoin_address(address: str) -> bool:
    if address.startswith('1') and 26 <= len(address) <= 35:
        return True
    elif address.startswith('3') and 34 <= len(address) <= 35:
        return True
    elif address.startswith('bc1') and 42 <= len(address) <= 62:
        return True
    else:
        return False

def print_ignored_addresses(ignored_addresses: list):
    if ignored_addresses:
        print("\nThe following lines in the input file were ignored because they are not valid Bitcoin addresses:")
        for address in ignored_addresses:
            print(address)
        for i in range(10, 0, -1):
            print(f"Continuing in {i} seconds...", end="\r")
            time.sleep(1)
        print("\nProceeding with the valid addresses...")
    else:
        print("bitcoin_addresses.txt - wallets integrity checked and all good")

def log_potentially_not_checked(last_wallet_address, addresses):
    if last_wallet_address not in addresses:
        print(f"Error: Last recorded wallet {last_wallet_address} not found in addresses list.")
        return
    last_index = addresses.index(last_wallet_address)
    start_index = max(0, last_index - 3)
    end_index = min(len(addresses), last_index + 4)
    nearby_wallets = addresses[start_index:end_index]
    with open(potentially_not_checked_file, 'a') as f:
        f.write(f"\n----------------------------------------\n")
        f.write(f"Date, Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        for wallet in nearby_wallets:
            f.write(f"{wallet}\n")
    print("Logged potentially unchecked wallets to Potentially_not_checked.txt")

def log_result(result: tuple[bool, str, str], counter: list, processed_wallets: list, time_estimator: TimeEstimator, addresses: list):
    success, wallet_address, message = result
    processed_wallets[0] += 1
    with open(failure_file, 'w') as f:
        f.write(f"Last Recorded Wallet : {wallet_address}\n")
        f.write(f"Number of Processed Wallets : {processed_wallets[0]}\n")
    if success:
        try:
            balance_info = json.loads(message)
            confirmed = float(balance_info.get('confirmed', 0))
            log_message = f"Address: {wallet_address}, Balance: {confirmed} BTC"
            print(f"Checking Kaya AI: {wallet_address}")
            if confirmed > 0:
                with open(positive_balance_file, 'a') as positive_file:
                    positive_file.write(f"Address: {wallet_address}, Balance: {confirmed} BTC\n")
        except json.JSONDecodeError as e:
            log_message = f"Address: {wallet_address}, Error parsing balance: {str(e)}"
    else:
        log_message = f"Address: {wallet_address}, Error: {message}"
        log_potentially_not_checked(wallet_address, addresses)
    print(log_message)
    counter[0] -= 1
    elapsed_time = time.time() - time_estimator.start_time
    time_estimator.start_time = time.time()
    time_estimator.update(elapsed_time)
    remaining_time = time_estimator.estimate_remaining_time(counter[0])
    if remaining_time is not None:
        remaining_hours = int(remaining_time // 3600)
        remaining_minutes = int((remaining_time % 3600) // 60)
        print(f"Remaining wallets to process: {counter[0]} - Estimated remaining time {remaining_hours}H{remaining_minutes}MN")
    else:
        print(f"Remaining wallets to process: {counter[0]} - Remaining time under calculation")

def handle_failure_file():
    """
    Reads failure.txt and prompts the user to either start over or resume.
    Returns (last_wallet_address, processed_wallets).
    """
    last_wallet_address = None
    processed_wallets = 0
    try:
        with open(failure_file, 'r') as f:
            lines = f.readlines()
            if len(lines) >= 2:
                last_wallet_line = lines[0].strip().split(': ')
                processed_wallets_line = lines[1].strip().split(': ')
                if len(last_wallet_line) == 2:
                    last_wallet_address = last_wallet_line[1]
                if len(processed_wallets_line) == 2 and processed_wallets_line[1].isdigit():
                    processed_wallets = int(processed_wallets_line[1])
    except Exception as e:
        print(f"Error reading failure.txt: {e}")
    if not last_wallet_address:
        print("Warning: last_wallet_address is empty or failure.txt is malformed.")
        return None, 0
    print(f"Last recorded wallet: {last_wallet_address}")
    print(f"Number of wallets processed: {processed_wallets}")
    choice = input("""
Failure file detected:
[Y] Start over and reset failure.txt?
[N] Continue from the last recorded wallet?
Please enter Y or N: """).strip().upper()
    if choice == 'Y':
        with open(failure_file, 'w') as f:
            f.write("Last Recorded Wallet : \n")
            f.write("Number of Processed Wallets : 0\n")
        print("Resetting progress. Starting from the beginning.")
        return None, 0  # Reset to start from the beginning
    elif choice == 'N':
        print("Continuing from the last recorded wallet.")
        return last_wallet_address, processed_wallets
    else:
        print("Invalid input. Please enter Y or N.")
        return handle_failure_file()  # Retry if input is invalid


### Asynchronous Balance Check and Worker

async def check_balance(address: str, connectivity_event: asyncio.Event) -> tuple[bool, str]:
    """
    Waits for connectivity/Electrum to be available then runs the balance check asynchronously.
    """
    await connectivity_event.wait()
    try:
        proc = await asyncio.create_subprocess_exec(
            electrum_path, 'getaddressbalance', address,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            return True, stdout.decode().strip()
        else:
            return False, stderr.decode().strip()
    except Exception as e:
        return False, str(e)

async def worker(address: str, connectivity_event: asyncio.Event, semaphore: asyncio.Semaphore) -> tuple[bool, str, str]:
    async with semaphore:
        success, message = await check_balance(address, connectivity_event)
        return success, address, message


### Main Asynchronous Function

async def main():
    # Ensure connectivity before starting.
    await initial_safeguard_check_async()

    # Create an asyncio.Event for connectivity and start the monitor.
    connectivity_event = asyncio.Event()
    connectivity_event.set()  # Assume connectivity is initially available.
    monitor_task = asyncio.create_task(monitor_connectivity(connectivity_event))

    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} does not exist.")
        return

    with open(input_file, 'r') as f:
        addresses = [line.strip() for line in f if line.strip()]

    # Handle failure file and filter addresses.
    last_wallet_address, processed_wallets = None, 0
    if os.path.exists(failure_file):
        last_wallet_address, processed_wallets = handle_failure_file()
    if last_wallet_address is None:
        valid_addresses = []
        ignored_addresses = []
        for address in addresses:
            if is_valid_bitcoin_address(address):
                valid_addresses.append(address)
            else:
                ignored_addresses.append(address)
        print_ignored_addresses(ignored_addresses)
        addresses = valid_addresses
    if last_wallet_address:
        try:
            last_index = addresses.index(last_wallet_address)
        except ValueError:
            last_index = 0
    else:
        last_index = 0

    total_wallets = len(addresses)
    remaining_wallets = total_wallets - processed_wallets
    print(f"Total wallets to process: {total_wallets}")
    print(f"Remaining wallets to process: {remaining_wallets}")

    counter = [remaining_wallets]
    processed_wallets_list = [processed_wallets]
    time_estimator = TimeEstimator()

    # Limit concurrency (for example, 10 simultaneous subprocesses).
    semaphore = asyncio.Semaphore(10)

    # Create a list of tasks for each address.
    tasks = [
        worker(address, connectivity_event, semaphore)
        for address in addresses[last_index:]
    ]

    # Process tasks as they complete.
    for future in asyncio.as_completed(tasks):
        result = await future
        log_result(result, counter, processed_wallets_list, time_estimator, addresses)

    # Cancel the connectivity monitor.
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass

if __name__ == '__main__':
    asyncio.run(main())

