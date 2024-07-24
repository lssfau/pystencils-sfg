import os
import glob
import subprocess

GROUPS = ["guide_generator_scripts"]
THIS_DIR = os.path.split(__file__)[0]


def main():
    for group in GROUPS:
        group_folder = os.path.join(THIS_DIR, group)

        for group_entry in os.listdir(group_folder):
            scripts_dir = os.path.join(group_folder, group_entry)
            if os.path.isdir(scripts_dir):
                query = os.path.join(scripts_dir, "*.py")
                for script in glob.glob(query):
                    subprocess.run(["python", script], cwd=scripts_dir).check_returncode()


if __name__ == "__main__":
    main()
