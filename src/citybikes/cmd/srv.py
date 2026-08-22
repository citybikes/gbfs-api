import subprocess
import sys

# death to argparse
if __name__ == "__main__":
    try:
        r = subprocess.run(["uvicorn", "citybikes.gbfs.app:app"] + sys.argv[1:], check=False)
        sys.exit(r.returncode)
    except KeyboardInterrupt:
        pass
