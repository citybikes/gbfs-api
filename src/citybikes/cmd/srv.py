import sys
import subprocess


# death to argparse
if __name__ == "__main__":
    try:
        r = subprocess.run(["uvicorn", "citybikes.gbfs.app:app"] + sys.argv[1:])
        sys.exit(r.returncode)
    except KeyboardInterrupt:
        pass
