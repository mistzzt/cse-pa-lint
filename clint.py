import subprocess
import json
import os
import difflib
import argparse
import sys

KEY_PRE_TASK = 'PreTasks'
KEY_CMD = 'Command'

KEY_STDIN = 'stdin'
KEY_STDOUT = 'stdout'
KEY_STDERR = 'stderr'

INDEX_STDOUT = 0
INDEX_STDERR = 1

INDEX_ACTION_TYPE = 0
INDEX_LINE = 1

NEW_LINE = '\n'
USELESS_NEW_LINE = '\r'
EXIT_SUCCESS = 0
EXIT_FAILURE = 1

CHANGED_CONFIG_FORMAT = '{}.new'


def parse_args():
    parser = argparse.ArgumentParser(description='Validate command line interface program output')
    parser.add_argument('config', metavar='config', type=str, nargs=1, help='project to be processed')
    parser.add_argument('--init', action='store_true', help="initialize new programming assignments")

    return parser.parse_args()


def run_program(file_name):
    config = read_file(file_name)

    pre_tasks = config[KEY_PRE_TASK]
    for task in pre_tasks:
        os.system(task)

    cmd = config[KEY_CMD]
    stdin = config[KEY_STDIN]

    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = p.communicate(NEW_LINE.join(stdin).encode('UTF-8'))

    invoke_diff(config, output)
    write_file(CHANGED_CONFIG_FORMAT.format(file_name), cmd, stdin, output[INDEX_STDOUT], output[INDEX_STDERR])


def invoke_diff(config, output):
    config_stdout = config[KEY_STDOUT]
    config_stderr = config[KEY_STDERR]

    stdout = strip_array_string(convert_byte_string(output[INDEX_STDOUT]).split(NEW_LINE))
    stderr = strip_array_string(convert_byte_string(output[INDEX_STDERR]).split(NEW_LINE))

    differ = difflib.Differ()
    diff = differ.compare(config_stdout, stdout)
    print(NEW_LINE.join(diff))

    diff = differ.compare(config_stderr, stderr)
    print(NEW_LINE.join(diff))


def write_file(file_name, cmd, stdin, stdout, stderr):
    stdout = strip_array_string(convert_byte_string(stdout).split(NEW_LINE))
    stderr = strip_array_string(convert_byte_string(stderr).split(NEW_LINE))

    with open(file_name, 'w') as config:
        config.write(json.dumps(
            {
                KEY_PRE_TASK: [],
                KEY_CMD: cmd,
                KEY_STDIN: stdin,
                KEY_STDOUT: stdout,
                KEY_STDERR: stderr
            }, indent=4))


def read_file(file_name):
    with open(file_name, 'r') as config:
        return json.load(config)


def convert_byte_string(array):
    if not isinstance(array, type('')):
        array = array.decode('UTF-8').replace(USELESS_NEW_LINE, '')

    return array


def strip_array_string(array):
    if len(array) == 1 and array[0] == '':
        return []

    return array


def error(msg):
    """ Show error message to user. """
    sys.stderr.write('> \033[93m{} \033[0m\n'.format(msg))


args = parse_args()
config_path = args.config[0]

if args.init:
    write_file(config_path, "command name", ["standard input"], "standard output", "standard error")
    exit(EXIT_SUCCESS)

if not os.path.exists(config_path) and not args.init:
    error('Config file does not exist: {}'.format(config_path))
    exit(EXIT_FAILURE)

run_program(config_path)
