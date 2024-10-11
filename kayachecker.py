import subprocess
from multiprocessing import Pool
import json
import os
    #2024 oct - added bitcoin_addresses.tx count and decrementing counter 
    # prefer to use electrum portable since standalone gave me trouble 
    # output file for positive balance only 
    # very minor adjustments

print("Github: @kayaaicom")

# Define input and output file paths
input_file = r'c:\\Your _path\\bitcoin_addresses.txt'
output_file = r'c:\\Your _path\\log.txt'
positive_balance_file = r'c:\\Your _path\\walletwithbalance.txt'

def check_balance(address: str) -> tuple[bool, str]:
    """
    Check the balance of a Bitcoin address using Electrum.

    Args:
        address (str): The Bitcoin address to check.

    Returns:
        tuple[bool, str]: A tuple containing success status and either the balance or an error message.
    """
    try:
        # Call Electrum to check the address balance
        result = subprocess.run(
            [r'c:\\Your _path\\electrum-4.5.5-portable.exe', 'getaddressbalance', address], 
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)

def log_result(result: tuple[bool, str, str], counter: list):
    """
    Log the result of the balance check and decrement the counter.

    Args:
        result (tuple[bool, str, str]): A tuple containing the success status, address, and result message.
        counter (list): A list used to track the remaining wallets to be processed (mutable object).
    """
    success, address, message = result

    if success:
        try:
            # Parse the balance info safely
            balance_info = json.loads(message)
            confirmed = float(balance_info.get('confirmed', 0))
            log_message = f"Address: {address}, Balance: {confirmed} BTC"
            print(f"Checking Kaya AI: {address}")
            
            # Save wallets with positive balances to a separate file
            if confirmed > 0:
                with open(positive_balance_file, 'a') as positive_file:
                    positive_file.write(f"Address: {address}, Balance: {confirmed} BTC\n")

        except json.JSONDecodeError as e:
            log_message = f"Address: {address}, Error parsing balance: {str(e)}"
    else:
        log_message = f"Address: {address}, Error: {message}"

    # Log to file
    with open(output_file, 'a') as log:
        log.write(log_message + '\n')

    print(log_message)

    # Decrement the counter and display remaining addresses
    counter[0] -= 1
    print(f"Remaining wallets to process: {counter[0]}")

def worker(address: str, counter: list) -> tuple[bool, str, str]:
    """
    Worker function to check the balance of a single Bitcoin address.

    Args:
        address (str): The Bitcoin address to check.
        counter (list): A list used to track the remaining wallets.

    Returns:
        tuple[bool, str, str]: The result of the balance check including the address.
    """
    success, message = check_balance(address)
    return success, address, message  # Return the address with the result

if __name__ == '__main__':
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} does not exist.")
        exit(1)

    # Read addresses from the input file
    with open(input_file, 'r') as f:
        addresses = f.read().splitlines()

    # Initialize the counter with the total number of addresses
    total_wallets = len(addresses)
    counter = [total_wallets]  # Using a list to allow mutability (can modify it within worker)

    print(f"Total wallets to process: {total_wallets}")

    # Create a pool of workers to check multiple addresses in parallel
    pool = Pool(5)
    for address in addresses:
        pool.apply_async(worker, args=(address, counter), callback=lambda result: log_result(result, counter))

    pool.close()
    pool.join()
