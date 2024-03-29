import argparse
import unittest

def run_test(test_file: str = None, test_case: str = None):
    loader = unittest.TestLoader()
    start_dir = 'tests'

    if test_file:
        suite = loader.discover(start_dir, pattern=test_file)
    elif test_case:
        suite = loader.discover(start_dir)
        for tests in suite:
            for test in tests:
                for case in test:
                    if case._testMethodName == test_case:
                        test_suite = unittest.TestSuite()
                        test_suite.addTest(case)
                        runner = unittest.TextTestRunner(failfast=True)
                        runner.run(test_suite)
                        return
    else:
        suite = loader.discover(start_dir)

    runner = unittest.TextTestRunner(failfast=True)
    runner.run(suite)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provide test file, test case, or nothing to run test suite")
    parser.add_argument("--tf", nargs='?', type=str, help="Test file.")
    parser.add_argument("--tc", nargs='?', type=str, help="Test case.")

    args = parser.parse_args()

    test_file = args.tf
    test_case = args.tc

    if test_file and test_case:
        raise Exception('Please provide either a test case or a test file.')

    if test_file:
        print(f'Test file to be run: {test_file}')

    if test_case:
        print(f'Test case to be run: {test_case}')

    run_test(test_file=test_file, test_case=test_case)
