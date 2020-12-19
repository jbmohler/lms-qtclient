# Define your CI/CD pipeline in a Python script.

import conducto as co


installation = """
set -e

python3 -m venv ~/venv
. ~/venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
"""


# `pr()` creates and returns a CI/CD pipeline for a Pull Request. Run from the command
# line with `python pipeline.py pr --branch=<branch>`.
def pr(branch) -> co.Parallel:
    # Make a Docker image, based on python:alpine, with the whole repo and the contents
    # of the given branch.
    image = co.Image("python:3.8", copy_repo=True, copy_branch=branch)

    # Using that Docker image, run three commands in parallel to interact with the
    # repo's files.
    with co.Parallel(image=image) as root:
        co.Exec(f"echo {branch}", name="print branch")
        co.Exec("ls -la", name="list files")
        with co.Serial(
            image=image,
            name="checks",
            container_reuse_context=co.ContainerReuseContext.NEW,
        ):
            co.Exec("pip install black flake8", name="install")
            co.Exec("git ls-files '*.py' | xargs black --check", name="formatting")
            co.Exec("git ls-files '*.py' | xargs flake8", name="linting")
        co.Exec(installation, name="dependencies")

    co.git.apply_status_all(root)

    return root


if __name__ == "__main__":
    co.main()
