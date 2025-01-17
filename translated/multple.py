import subprocess
import os

def verify_paths(script_paths):
    """
    Verify that all script paths exist.

    :param script_paths: List of paths to Python scripts to verify.
    :return: A tuple containing two lists - valid paths and invalid paths.
    """
    valid_paths = []
    invalid_paths = []

    for script in script_paths:
        if os.path.isfile(script):
            valid_paths.append(script)
        else:
            invalid_paths.append(script)

    return valid_paths, invalid_paths

def run_scripts(script_paths):
    """
    Run a list of Python scripts in order.

    :param script_paths: List of paths to Python scripts to run.
    """
    for script in script_paths:
        try:
            print(f"Running script: {script}")
            result = subprocess.run(["python", script], check=True, text=True, capture_output=True)
            print(f"Output from {script}:")
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error running {script}: {e}")
            print(f"Error output: {e.stderr}")
        except Exception as e:
            print(f"Unexpected error while running {script}: {e}")
        finally:
            print(f"Finished attempting to run: {script}\n")

if __name__ == "__main__":
    # Define the list of script paths
    script_paths = [
        "small100/main1.py",  # Replace with the actual path to your script
        #"madlad400-3b-mt/main1.py",  # Replace with the actual path to your script
        #"NLLB/main1.py",  # Replace with the actual path to your script
        # "script3.py"   # Replace with the actual path to your script
    ]

    # Verify the script paths
    valid_paths, invalid_paths = verify_paths(script_paths)

    if invalid_paths:
        print("The following script paths are invalid:")
        for invalid_path in invalid_paths:
            print(f"- {invalid_path}")
        print("Please correct the paths and try again.")
    else:
        # Call the function to run the scripts
        run_scripts(valid_paths)
