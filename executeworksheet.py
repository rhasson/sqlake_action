#!/usr/bin/python3

## Parses a SQLake Worksheet and executes each command using the Upsolver CLI ##
import os
import re
import sys
import json
import getopt
import subprocess
from typing import NamedTuple

class QueryResults (NamedTuple):
    worksheet: str # worksheet path and name
    order: int # order of exeuction
    query: str # query string
    out: str # output from the execution
    err: str # error from the execution

def main():
    worksheet_path = ''
    file_list = ''
    local_path = ''
    print('Starting to parse and execute worksheets')

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hf:w:o:')
        if not opts:
            print('executeworksheet.py -f <list_of_files> | -w <path_to_sql> -o <output_path>')
            exit(2)
    except getopt.GetoptError:
        print('executeworksheet.py -f <list_of_files> | -w <path_to_sql> -o <output_path>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('executeworksheet.py -f <list_of_files> | -w <path_to_sql> -o <output_path>')
            sys.exit()
        elif opt == '-f':
            file_list = arg.split(',')
            if len(file_list) > 0:
                files = getfilelist(file_list)
            else:
                print('when using -f you must provide a comma separated list of SQL filenames and relative path '+arg)
        elif opt == '-w':
            if os.path.exists(arg):
                files = getworksheets(arg)
            else:
                print('could not find a SQL file in the given path '+arg)
                sys.exit(2)
        elif opt == '-o':
            if os.path.exists(arg):
                local_path = arg
            else:
                print('you must provide an output path to write the execution results')
                sys.exit(2)
        else:
            print('No args found')
            sys.exit(2)
    
    results = []
    for file in files:
        sql_cmd = splitworksheet(file)
        c = 1
        for cmd in sql_cmd:
            if c <= len(sql_cmd):
                try:
                    print('Executing {0}: {1}'.format(c, cmd))
                    res = subprocess.run(
                        ['upsolver', '-c', '/config', 'execute', "-c", "{}".format(cmd)], capture_output=True, text=True, check=True
                    )
                    results.append(QueryResults(file, c, cmd, res.stdout, res.stderr))
                    c += 1
                except subprocess.CalledProcessError as e:
                    print('Query execution failed: {}'.format(e.stderr))
                    results.append(QueryResults(file, c, cmd, '', e.stderr))
                    sys.exit(2)

        print('Finished executing {} \r\n'.format(os.path.basename(file)))
    
    writeresults(results, local_path)
        
## walk the input path
## return a list of .sql files (assumed to be worksheets)
def getworksheets(input_path):
    print('Looking for SQL files in {}'.format(input_path))
    worksheets = []
    for path, subdirs, files in os.walk(input_path):
        for name in files:
            fullpath = path + '/' + name
            print('full path: {}'.format(fullpath))

            name, file_ext = os.path.splitext(fullpath)
            if file_ext.lower() in ['.sql']:
                worksheets.append(fullpath)

    worksheets.sort()
    return worksheets

## iterate over file list, check if SQL file and return sorted list
def getfilelist(items):
    print('Checking file list {}'.format(items))
    worksheets = []
    for item in items:
        name, file_ext = os.path.splitext(item)
        if file_ext.lower() in ['.sql']:
            worksheets.append(item)
    
    worksheets.sort()
    return worksheets

## read each worksheet, and split it on ;
## return a list of sql commands to execute
def splitworksheet(path):
    print('Spliting SQL file in {}'.format(path))
    cmds = []
    fd = open(path, 'r')
    ws_file = fd.read()
    fd.close()

    s = re.sub(re.compile("/\*.*?\*/",re.DOTALL) ,"" ,ws_file)
    s = re.sub(re.compile("//.*?\n") ,"" ,s)
    s = re.sub(re.compile("--.*?\n") ,"" ,s)

    sql_commands = s.split(';')
    
    for s in sql_commands:
        s = s.strip()
        if s:
            s = s + ';'
            cmds.append(s)

    return cmds

## write the worksheet execution results to a temp file
def writeresults(data, local_path):
    print('Writing execution results to {}'.format(local_path))
    if len(data) > 0:
        md = formatoutput(data)
    else:
        md = '**Could not find SQL files to execute** \r\n\r\n'
    with open(local_path + '/execution_output.md', 'a', encoding='utf-8') as fd:
        fd.write(md)

def formatoutput(data):
    output = '## Upsolver SQLake Execution Summary \r\n\r\n'
    for i in data:
        output += '### **{}** \r\n\r\n'.format(i.worksheet)
        output += '--- \r\n\r\n'
        output += '**Query position in Worksheet:** {} \r\n\r\n'.format(i.order)
        output += '**Query text:** `{}` \r\n\r\n'.format(i.query)
        output += '**Results:** `{}` \r\n\r\n'.format(i.out)
        output += '**Errors:** `{}` \r\n\r\n'.format(i.err)

    return output

if __name__ == '__main__':
  main()