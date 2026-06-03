Contributing to Hermes-DM
=========================

First off, thank you for considering contributing to Hermes-DM!

This project is open-source, meaning it is built and maintained by people just like you. Whether you are a seasoned hardware engineer, a Python expert, or a beginner just learning how to use Git, your help is deeply appreciated.

You Don't Need to Write Code to Help!
-------------------------------------

Code contributions are wonderful, but they are only one part of maintaining a healthy project. We highly value non-code contributions, such as:

* **Improving Documentation:** Did you find a typo? Was a sentence in this documentation confusing? Did you figure out a clever way to use the library that isn't documented yet? Please submit a Pull Request! Keeping documentation clear and up-to-date is incredibly valuable.
* **Reporting Bugs:** If something isn't working as expected, open an Issue on GitHub. Please include your OS, the version of Hermes-DM you are using, and the traceback if applicable.
* **Suggesting Features:** Have an idea for a new instrument driver or a core feature? Open an Issue so we can discuss it!

How to Submit a Pull Request (PR)
---------------------------------

If you want to contribute code or documentation changes, please follow these steps:

1. **Fork the Repository:** Click the "Fork" button on GitHub to create your own copy of the project.
2. **Clone Locally:** Clone your fork to your local machine.
3. **Set Up the Environment:** Follow the steps in the :doc:`installation` guide to set up your virtual environment, install the development dependencies, and activate the ``pre-commit`` hooks.
4. **Create a Branch:** Create a branch for your feature or fix:

   .. code-block:: bash

      git checkout -b feature/my-new-idea

5. **Make Your Changes:** Write your code, update the tests, and modify the documentation if necessary.
6. **Commit and Push:** Commit your changes. Our ``pre-commit`` hooks will automatically check your formatting and linting before the commit succeeds.
7. **Open a PR:** Go to the original Hermes-DM repository on GitHub and open a Pull Request against the ``main`` branch.

Code Quality and Testing Standards
----------------------------------

To keep the codebase clean and stable, we enforce a few automated checks on all Pull Requests:

* **Formatting and Linting:** We use ``ruff``. Your code will automatically be formatted when you commit if you have installed the pre-commit hooks.
* **Testing:** We use ``pytest``. If you add a new feature, please add a test for it. Ensure all existing tests pass before submitting your PR by running ``pytest -v`` locally.
* **Continuous Integration:** When you open a PR, GitHub Actions will automatically run our test suite and linting checks across multiple operating systems. Don't worry if it fails the first time—you can just push a fix to your branch and it will run again!

We look forward to seeing your contributions!
