#!/software/common64/python/bin/python

import os
import sys
import argparse
import json
import subprocess
import glob
import shutil

HOME = os.path.expanduser('~/')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKSTYLE_PATH = os.path.join(SCRIPT_DIR, 'bin', 'checkstyle-8.3-all.jar')
STYLE_CONFIG_PATH = os.path.join(SCRIPT_DIR, 'bin', 'google_checks.xml')
FORMATTER_PATH = os.path.join(SCRIPT_DIR, 'bin', 'google-java-format-1.6-SNAPSHOT-CSE11-all-deps.jar')

CONFIG_FILE_NAME = 'config.json'
COMPILE_ERROR_FILE_NAME = 'compile_error.log'
STYLE_ERROR_FILE_NAME = 'style_error.log'

ERROR_STOP_MESSAGE = 'Exit now?'

EXIT_SUCCESS = 0
EXIT_FAILURE = 1


def parse_args():
    parser = argparse.ArgumentParser(description='Process CSE Programming Assignments')
    parser.add_argument('project', metavar='project', type=str, nargs=1, help='project to be processed')
    parser.add_argument('--init', action='store_true', help="initialize new programming assignments")

    return parser.parse_args()


def check_selection(prompt):
    """ Prompt the user for a yes/no question. """

    sys.stdout.write(prompt + ' [y/n] ')
    answer = sys.stdin.readline().strip().lower()

    if answer == 'yes' or answer == 'y':
        return True
    return False


def init():
    """ Initialize a new project folder. """
    values = None

    if os.path.exists(project_directory):
        if not os.path.exists(configuration_path):
            os.chdir(project_directory)
            files = glob.glob('*.java')
            libs = glob.glob('*.jar')

            values = dict(Files=files, OptionalFiles=list(), Libraries=libs)
        else:
            if not check_selection('Project directory already exists. Do you still want to create a new one?'):
                return
            path = project + '.old'
            if os.path.exists(path):
                shutil.rmtree(path)
            os.rename(project_directory, path)

    if values is None:
        values = dict(Files=list(), OptionalFiles=list(), Libraries=list())
        os.mkdir(project_directory)

    with open(configuration_path, 'w') as config:
        config.write(json.dumps(values, indent=4))


def process_project():
    """ Process Programming Assignment project. """

    if not os.path.exists(configuration_path):
        error('Configuration does not exist.')
        return

    with open(configuration_path) as data_file:
        data = json.load(data_file)

    files = data['Files']
    optional_files = data['OptionalFiles']
    libraries = data['Libraries']

    if len(files) == 0:
        error('No files will be processed.')
        return EXIT_FAILURE

    print('\n')
    print('Start checking files...')
    result = check_files(files, optional_files, libraries)
    if result:
        if check_selection(ERROR_STOP_MESSAGE):
            return EXIT_FAILURE
    print('Completed!')

    print('\n')
    print('Start formatting file...')
    format_code(files, optional_files)
    print('Completed!')

    print('\n')
    print('Start checking style...')
    result = check_style(files, optional_files)
    if result:
        if check_selection(ERROR_STOP_MESSAGE):
            return EXIT_FAILURE
    print('Completed!')

    print('\n')
    print('Start checking line width...')
    check_line_width(files, optional_files)
    print('Completed!')

    print('\n')
    print('Start compiling files...')
    result = test_compile(files, optional_files, libraries)
    if result:
        if check_selection(ERROR_STOP_MESSAGE):
            return EXIT_FAILURE
    print('Completed!')

    print('\n')
    print('Performing cleanup...')
    cleanup()
    print('Completed!')


def check_files(files, optionals, libraries):
    has_error = False

    for name in files:
        path = os.path.join(project_directory, name)
        if not os.path.exists(path):
            error(name + " does not exist.")
            has_error = True

    for name in optionals:
        path = os.path.join(project_directory, name)
        if not os.path.exists(path):
            error(name + " does not exist.")
            has_error = True

    for lib in libraries:
        path = os.path.join(project_directory, lib)
        if not os.path.exists(path):
            error(lib + " does not exist.")
            has_error = True

    return has_error


def test_compile(files, optionals, libraries):
    has_error = False
    libs = list()
    for lib in libraries:
        libs.append('./' + lib + ':')

    class_path = ''.join(libs) + '.'
    cmd = 'javac -cp {} {}'

    result = subprocess.check_output(cmd.format(class_path, ' '.join(files)), shell=True)
    if len(result) != 0:
        error('Your source codes cannot be compiled; see {} for details.'.format(COMPILE_ERROR_FILE_NAME))
        has_error = True

    if len(optionals) != 0:
        result = subprocess.check_output(cmd.format(class_path, ' '.join(optionals)), shell=True)
        if len(result) != 0:
            error('Your optional files cannot be compiled; see {} for details.'.format(COMPILE_ERROR_FILE_NAME))
            has_error = True

    return has_error


def check_style(files, optionals):
    java_files = ' '.join(files) + ' '.join(optionals)
    cmd = 'java -jar {} -c {} {}'.format(CHECKSTYLE_PATH, STYLE_CONFIG_PATH, java_files)

    result = subprocess.check_output(cmd, shell=True)

    if len(result) != 0:
        error('You have style error in your source files: See {} for details.'.format(STYLE_ERROR_FILE_NAME))
        with open(STYLE_ERROR_FILE_NAME, 'w') as log:
            log.writelines(result)
        return True

    return False


def check_line_width(files, optionals):
    cmd = 'grep -n \'.\\{81,\\}\' '

    for name in files:
        print('Checking line width in ' + name)
        os.system(cmd + name)

    for name in optionals:
        print('Checking line width in ' + name)
        os.system(cmd + name)


def format_code(files, optionals):
    """ Format source files using google java formatter and show diff to user. """
    backup_folder = 'bak'

    if os.path.exists(backup_folder):
        shutil.rmtree(backup_folder)

    os.mkdir(backup_folder)
    os.system('cp *.java {}/.'.format(backup_folder))

    cmd = 'java -jar {} --replace {}'.format(FORMATTER_PATH, ' '.join(files))
    os.system(cmd)

    if len(optionals) != 0:
        cmd = 'java -jar {} --replace {}'.format(FORMATTER_PATH, ' '.join(optionals))
        os.system(cmd)

    for name in files:
        print('\n')
        print('Showing diff of file {} ...'.format(name))

        status = os.system('diff {0} {1}/{0}'.format(name, backup_folder))
        if status == 0:
            continue

        if not check_selection('Do you want to keep the change in file {}?'.format(name)):
            os.system('cp {}/{} .'.format(backup_folder, name))
            print('Reverted file ' + name)

    for name in optionals:
        print('\n')
        print('Showing diff of file {} ...'.format(name))

        status = os.system('diff {0} {1}/{0}'.format(name, backup_folder))
        if status == 0:
            continue

        if not check_selection('Do you want to keep the change in file {}?'.format(name)):
            os.system('cp {}/{} .'.format(backup_folder, name))
            print('Reverted file ' + name)


def cleanup():
    """ Clean compiled class files. """
    os.system('rm *.class')


def error(msg):
    """ Show error message to user. """
    sys.stdout.write('[Error] ' + msg + '\n')


args = parse_args()
project = args.project[0]

project_directory = os.path.expanduser(os.path.join(HOME, project))
configuration_path = os.path.expanduser(os.path.join(HOME, project, CONFIG_FILE_NAME))

os.chdir(HOME)

if args.init:
    init()
    exit(EXIT_SUCCESS)

if not os.path.exists(project_directory) and not args.init:
    error('PA folder does not exist: {}'.format(project_directory))
    exit(EXIT_FAILURE)

os.chdir(project_directory)
code = process_project()
exit(code)
