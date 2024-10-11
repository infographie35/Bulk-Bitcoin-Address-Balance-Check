<h1>Bitcoin Address Balance Check</h1>

![Profil Picture](https://raw.githubusercontent.com/kayaaicom/Electrum-Bitcoin-Address-Balance-Checker/main/test.png)

In the image, it says x.py in the test phase, ignore it and run python name.py.

<br>
FOR THE PROGRAM TO WORK, DO NOT FORGET TO OPEN THE ELECTRUM WALLET AND RUN ELECTRUM IN THE BACKGROUND.<br>
<br>
This Python script is used to check the balances of a large number of Bitcoin addresses via Electrum. Below you can find detailed information on how to use this project.

<h2>User Guide</h1>
Summary of the Updated Code Compared to the Original

1. Improved Wallet Processing and Tracking

Failure Recovery: The updated code has improved functionality to handle failures gracefully. It creates a file named failure.txt to record progress, including the last successfully processed wallet and the number of wallets already processed. This allows users to either resume from where they left off or restart from the beginning if an interruption occurs.

In the original version, there wasn't as robust a mechanism for resuming after failure.

2. Estimated Remaining Time Calculation

Time Estimator Class: The updated code includes a TimeEstimator class that calculates an estimated remaining time for the wallet processing. It uses a rolling average of the last 200 wallets to provide a more accurate estimate of time remaining, which is displayed during processing.

The original version lacked this feature entirely, offering no information about how long the script would take to complete processing.

3. Handling Invalid Bitcoin Addresses

Validation Step: The updated code adds a validation step using the is_valid_bitcoin_address() function to check each address's validity before processing. Any invalid addresses are listed, and the user is given a 10-second countdown before proceeding with valid addresses.

The original version did not include this validation step, which could lead to wasted time and errors when trying to process invalid addresses.

4. Output Files and Their Purpose

Positive Balance File (walletwithbalance.txt): This file stores Bitcoin addresses that have a non-zero balance. It allows users to easily identify which addresses contain funds.

The original version also had this feature.

Failure File (failure.txt): This is a new addition in the updated code. It records the last processed wallet and the number of wallets processed. This file is crucial for resuming processing after an interruption, providing an option to either start fresh or continue from the last point.

The original version lacked such a mechanism for handling interruptions, forcing users to restart from scratch after any failure.

5. User Interaction for Resuming

Choice to Resume or Restart: The updated code asks the user if they want to resume from where they left off or start over if a failure file is detected. This user-friendly prompt helps in continuing the process smoothly without manual intervention.

The original version did not provide this flexibility, and users would have to manually handle interruptions.

6. Concurrency and Parallel Processing

Worker Pool: Both versions of the code use multiprocessing (Pool) to process multiple wallets concurrently. However, the updated version has more structured handling of shared state variables (counter, processed_wallets) for remaining and processed wallets, reducing the chances of errors.

Files Created by the Code

walletwithbalance.txt: Stores Bitcoin addresses that have a positive balance.

failure.txt: Records the last processed wallet and the number of wallets already processed. It allows the user to resume processing after an interruption.

Key Differences in Code Approach

Time Tracking: The updated version uses the TimeEstimator class to estimate the remaining time, which significantly improves user experience by providing better transparency on the duration.

Error Handling: The updated code is more robust in terms of handling errors and interruptions, providing a way to resume progress without starting over.

Input Validation: The updated code validates all Bitcoin addresses before processing, saving time and preventing errors.

Overall, the updated version of the code is more user-friendly, resilient, and informative, offering a better experience with features like time estimation, failure recovery, and input validation.














Clone your project files to your computer or download and extract the ZIP file.

Create a text file called bitcoin_addresses.txt and add the Bitcoin addresses you want to check, line by line.

Open bitcoin_balance_checker.py in your project folder and update the input_file and output_file variables:

python
Copy code
# Define input and output file paths
input_file = r'c:\\Your _path\\bitcoin_addresses.txt'
positive_balance_file = r'c:\\Your _path\\walletwithbalance.txt'
failure_file = r'c:\\Your _path\\failure.txt'
# Electrum path
electrum_path = r'c:\\Your _path\\electrum-4.5.5-portable.exe'

These variables specify the path to the file with the input addresses and the path to the file where the results will be saved.

Run kayachecker.py using your Python interpreter:

    python kayachecker.py

The script will check each Bitcoin address through Electrum and positive balance will be recorded in a file called walletwithbalance.txt.

<h2>Requirements</h2>
To use this project you need the following requirements:

Python (version 3.x recommended)
Electrum wallet (you must have a workable version of Electrum installed on your computer)
Contribution
If you would like to contribute to this project or report issues, please create issues or pull requests via the GitHub repository.

<h2>License</h2>
This project is licensed under the MIT License.

All tools and information contained herein are presented or made available for the sole purpose of securing legal remedies. I do not undertake any illegal action on your part. FOR PURELY EDUCATIONAL PURPOSES.

<h3>Support:</h3>
<p><a href="https://www.buymeacoffee.com/kayaaicom"> <img align="left" src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" height="50" width="210" alt="kayaaicom" /></a></p><br><br>
<br><img src="https://bitcoin.org/img/icons/logotop.svg?1687792074" width="100" alt="BTC"><h4>1KAYAaiM83LP6BuviwsHRjvkXepMhy4nop</h4>
