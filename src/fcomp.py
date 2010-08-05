# -*- coding: utf-8 -*-
#! /usr/bin/env python
__author__ = "Vadim Bobrenok <vader-xai@yandex.ru>"

import sys
import os
import stat
import shutil
import filecmp
import difflib
import ConfigParser
import re
from itertools import cycle
from time import sleep



class FileComparator (object):
    def __init__(self, config_file = os.path.join(sys.path[0],"config.ini")):
             
        self.__read_config(config_file)
        self.update_nodes_list()
        
        
    def create_repo (self):
        """Copy files to repository"""        
        shutil.rmtree(self.repo_path, True)
        self.__create_directory(self.repo_path)
        
        bar = ProgressBar(len(self.nodes))
        failed = []
        for src, dest in self.nodes:
            try:               
                self.__copy_file(src, os.path.join(self.repo_path, dest))
            except IOError:
                failed.append([src, dest])
            bar.update()
            
        if len(failed)!=0:
            print "\n>> Following files haven't been copied and will be listed as missed files:\n"
            for fail in failed:
                print fail[0] + "\n"
            

    def compare_repo (self):
        """Compare files in repository with files from nodes_list"""
        shutil.rmtree(self.diff_dir, True)
        self.__create_directory(self.diff_dir)
        self.__create_directory(self.report_dir)
        
        changed_files = [] 
        removed_files = []
        new_files = []
        missed_files = []
    
        bar = ProgressBar(len(self.nodes))
        
        for src_file, repo_file in self.nodes:
            try:
                if not filecmp.cmp(src_file, os.path.join(self.repo_path, repo_file)):
                    self.__copy_file (src_file, os.path.join(self.diff_dir, repo_file))
                    changed_files.append([src_file, os.path.join(self.repo_path, repo_file)])
            except OSError:
                if os.path.isfile(os.path.join(self.repo_path, repo_file)):
                    removed_files.append([src_file, os.path.join(self.repo_path, repo_file)])
                else:
                    missed_files.append(src_file)
            bar.update()
  
        new_nodes = self.__build_nodes_list()[:]
        for node in new_nodes:
            if node not in self.nodes:
                new_files.append(node[0])

        return self.__write_report(self.__html_diff(changed_files), removed_files, new_files, missed_files)
    
    def update_nodes_list (self):
        self.nodes = self.__build_nodes_list()[:]
        
               
    def __read_config(self, config_file):
        """Read config file"""
        defaults = {"repo_path":(os.path.join(sys.path[0],"repo")),
                    "diff_dir":"__diff",
                    "report_dir":"__report",
                    "nodes_list": (os.path.join(sys.path[0],"nodes.txt")),
                    "regex_mode": "none",
                    "regex_act": "include"}
        config = ConfigParser.RawConfigParser(defaults)
        try:
            config.read(config_file)
    
            self.repo_path = config.get("Repository", "repo_path").strip('\\').strip('/')
            if self.repo_path == "": self.repo_path = os.path.join(sys.path[0],"")
            diff_dir = config.get("Repository", "diff_dir").strip('\\').strip('/')
            self.diff_dir = os.path.join(self.repo_path, diff_dir)
            report_dir = config.get("Repository", "report_dir").strip('\\').strip('/') 
            self.report_dir = os.path.join(self.diff_dir, report_dir)
            self.nodes_list = config.get("Repository", "nodes_list").strip('\\').strip('/')
            # Read RegexPath section if the regex_mode option is not "none"
            if config.get("RegexPath","regex_mode").lower() != "none":
                self.regex_path_mode = config.get("RegexPath","regex_mode").lower()
                if config.get("RegexPath","regex_act").lower() == "include":
                    self.regex_act = True
                else:
                    self.regex_act = False
                regex_dict = dict(config.items("RegexPath"))
                # Remove default values from regex_dict
                for key in defaults.keys():
                    del regex_dict[key]
                # Compile regular expressions
                self.regex_path_list=[]
                for key in regex_dict:
                    self.regex_path_list.append(re.compile(regex_dict[key]))
            else: 
                self.regex_path_mode = "none"
                self.regex_act = None
            # Read RegexDiff section if the regex_mode option is not "none"                    
            if config.get("RegexDiff","regex_mode").lower() != "none":      
                self.regex_diff_mode = config.get("RegexDiff","regex_mode").lower()
                regex_dict = dict(config.items("RegexDiff"))
                # Remove default values from regex_dict
                for key in defaults.keys():
                    del regex_dict[key]
                # Compile regular expressions
                self.regex_diff_list=[]
                for key in regex_dict:
                    self.regex_diff_list.append(re.compile(regex_dict[key]))
            else:
                self.regex_diff_mode = "none"                
                
        except:
            print "\n>> Config file '" +config_file+ "' doesn't exist or some sections are missed in config file.\n"
            sys.exit()

    def __build_nodes_list(self):
        """Build nodes list [[<absolute source path>, <relative path>], ...]"""
        try:
            nodes_file = open (self.nodes_list,'r')
        except IOError:
            print "\n>> File given as nodes list '" + self.nodes_list + "' doesn't exist."
            sys.exit()
            
        tmp_nodes = []
        for line in nodes_file:
            if line.strip('\n').strip().strip('\\').strip('/') == '': 
                continue
            tmp_nodes.append(line.strip('\n').strip().strip('\\').strip('/'))
        
        
        
        nodes = []
        for node in tmp_nodes:
            if os.path.isfile(node):
                if self.__regex_path(node):
                    nodes.append([node, os.path.splitdrive(node)[1].strip('\\').strip('/')])
            elif os.path.isdir(node):
                for root, dirs, files in os.walk(node):
                    for file in files:
                        if self.__regex_path(os.path.join(root,file)):
                            nodes.append([os.path.join(root,file), os.path.join(os.path.splitdrive(root)[1].strip('\\').strip('/'), file)])
            else:
                print "\n>> File or directory '" + node + "' doesn't exist.\n"
                while True:
                    command = raw_input("(I)gnore, (E)xit: ")
                    
                    if command.lower() == "i":
                        break
                    elif command.lower() == "e":
                        sys.exit()
                    else:
                        print ">> Invalid command. Please, make your choice. \n "
        
        nodes_file.close()
             
        if len(nodes) == 0: 
            print "\n>> Nothing to compare. File list is empty or there are no files matching regular expressions."
            sys.exit()
            
        return nodes
            
    def __regex_diff(self, path):
        """Compare current file path with regex objects list.
        True - differences report should be created for the file
        False - differences report shouldn't be created for the file"""
        if self.regex_diff_mode == "match":
            for regex_object in self.regex_diff_list:
                if regex_object.match(path) is not None: return True

        if self.regex_diff_mode == "search":
            for regex_object in self.regex_diff_list:
                if regex_object.search(path) is not None: return True
                
        return False

                                          
    def __regex_path(self, path):
        """Compare current file path with regex objects list.
        True - file should be included into file list
        False - file shouldn't be included into file list"""
        if self.regex_path_mode == "match":
            for regex_object in self.regex_path_list:
                if regex_object.match(path) is not None: return self.regex_act
                else: return not self.regex_act

        if self.regex_path_mode == "search":
            for regex_object in self.regex_path_list:
                if regex_object.search(path) is not None: return self.regex_act
                else: return not self.regex_act

        return True    
            
    
    def __copy_file (self, src, dest):
        """Copy file from <src> (abs path) to <dest> (abs path)"""
        dest = os.path.split(dest)[0]
        if os.path.splitdrive(os.path.split(src)[0])[1] != os.sep:
            if not os.path.exists(dest):
                self.__create_directory(dest)
            shutil.copy2(src, dest)
        else:
            shutil.copy2(src, dest)
        #Remove read only attribute from all files 
        os.chmod(os.path.join(dest,os.path.basename(src)), stat.S_IWRITE)
            
    def __create_directory (self, dir):
        """Create a new directory"""
        # Check if the folder exists, because shutil.rmtree works in Ignore Errors mode
        if not os.path.exists(dir):
            
            try:
                os.makedirs(dir)

            except OSError, IOError:
                # Windows hook. Windows raises an access denied error if the folder has been opened in Explorer before removal
                # So need to wait for a while between os.mkdirs attempts until the directory will be released by Explorer 
                if not os.path.exists(dir):
                    sleep(2)
                    try:
                        os.makedirs(dir)
                    except OSError, IOError:        
                        print ">> Directory path '" + dir + "' is invalid or access to the directory is denied"
                        sys.exit()
                        
    def __write_report (self, changed_files, removed_files, new_files, missed_files):
        """Create HTML report"""
        report = open(os.path.join(self.report_dir,r"report.htm"),"w+")
        report.write(
"""<html>
<head>
    <title>Differences report</title>
    <style type="text/css">
        body {font-family:'Courier New', Courier, monospace;}
            table {
                  font-family:'Courier New', Courier, monospace; border:medium; border: none
            }
            th, td {
                   border: 1px solid
            }
        a:link {color: #4b5cc3; text-decoration: none;}
        a:visited {color: #a0a0a0; text-decoration: none;}
        a:hover {color: #4b5cc3; text-decoration: underline;}
    </style>
</head>
<body>
<div style = 'min-width:1024px'>
    <strong>CHANGED FILES:</strong><br/><br/>
    <table width=90%>
    <col width=40%>
    <col width=40%>
    <col width=10%>
        <tr><th>Modified file</th><th>Original file (from repository)</th><th>Differences</th></tr>
            <tbody>"""
                    )
        for mod_file, orig_file, diff_file in changed_files:
            if diff_file != "":
                report.write("<tr><td><a href='file://"+mod_file +"'> "+ mod_file + " </a></td><td><a href='file://"+orig_file +"'> "+ orig_file + " </a></td><td><a href='file://"+diff_file +"'> View Differences </a></td></tr>\n")
            else:
                report.write("<tr><td><a href='file://"+mod_file +"'> "+ mod_file + " </a></td><td><a href='file://"+orig_file +"'> "+ orig_file + " </a></td><td>&nbsp;</td></tr>\n")
        report.write(
"""            </tbody>
    </table>
    <br/><br/>
    <strong>REMOVED FILES:</strong>
    <br/><br/>
    <table width=80%>
    <col width=40%>
    <col width=40%>
        <tr><th>Removed file</th><th>Original file (from repository)</th></tr>
            <tbody>"""
                    )
        for mod_file, orig_file in removed_files:
            report.write("<tr><td><a href='file://"+mod_file +"'> "+ mod_file + " </a></td><td><a href='file://"+orig_file +"'> "+ orig_file + " </a></td></tr>\n")
        report.write(
"""            </tbody>
    </table>
    <br/><br/>
    <strong>NEW FILES:</strong>
    <br/><br/>
    <table width=40%>
    <col width=40%>
        <tr><th>New File</th></tr>
            <tbody>"""
                    )
        for new_file in new_files:
            report.write("<tr><td><a href='file://"+new_file +"'> "+ new_file + " </a></td></tr>\n")
        report.write(
"""            </tbody>
    </table>
    <br/><br/>
    <strong>MISSED FILES:</strong>
    <br/><br/>
    <table width=40%>
    <col width=40%>
        <tr><th>Missed File</th></tr>
            <tbody>"""
                    )
        for missed_file in missed_files:
            report.write("<tr><td><a href='file://"+ missed_file +"'> "+ missed_file + " </a></td></tr>\n")
        report.write(
"""            </tbody>
    </table>
</div>
</body>
</html>"""
                     )
        report.close()
        return os.path.join(self.report_dir,r"report.htm")
    
    def __html_diff (self,changed_files):
        changed_files_diff=[]
        for mod_file, orig_file in changed_files:
            diff_file = os.path.join(self.report_dir, mod_file.replace(":","_").replace("\\","_").replace("/","_").replace(".","_")+".htm")
            if self.__regex_diff(diff_file): 
                diff_file_html = difflib.HtmlDiff().make_file(open(mod_file,"r").readlines(),open(orig_file,"r").readlines())
                diff_file_html_hook = diff_file_html.replace('<meta http-equiv="Content-Type"','',1).replace('content="text/html; charset=ISO-8859-1" />','',1).replace('Courier',"'Courier New', Courier, monospace",1)
                html_file = open(diff_file, "w")
                html_file.write(diff_file_html_hook)
                html_file.close()
                changed_files_diff.append([mod_file, orig_file, diff_file])
            else:
                changed_files_diff.append([mod_file, orig_file, ""])                
        return changed_files_diff
            
            
class ProgressBar(object):
    def __init__(self, steps, max_width=20):
        """Prepare the visualization."""
        self.max_width = max_width
        self.spin = cycle(r'-\|/').next
        
        # Bar template
        self.tpl = '%-' + str(self.max_width) + 's ] %c %3i%%' 
        if steps !=0: self.__show('[ ')
        
        # Current bar length
        self.last_output_length = 0
        
        # Amount of the steps
        self.steps = steps
        
        # Steps counter
        self.count = 0
        
        
    def update (self):
        """Update the visualization."""
        
        self.count = self.count + 1
        
        # Remove last state.
        self.__show('\b' * self.last_output_length)

        # Generate new state.
        width = int(float(self.count)/float(self.steps) * self.max_width)
        output = self.tpl % ('-' * width, self.spin(), float(self.count)/float(self.steps) * 100.0)

        # Show the new state and store its length.
        self.__show(output)
        self.last_output_length = len(output)
        
        # Add EOL when progress bar is full.
        if width == self.max_width: self.__show('\n')
        
    def __show(self, string):
        """Show strings in STDOUT""" 
        sys.stdout.write(string)
        sys.stdout.flush()
        

if __name__ == "__main__":
    comparator = FileComparator()
    print "\nType 'help' for instructions.\n"
    while True:
        command = raw_input("\n(N)odes, (R)epository, (C)ompare, (E)xit: ")
        
        if command.lower() == "r":
            comparator.create_repo()
        elif command.lower() == "c":
            if "win" in sys.platform.lower():
                os.system(comparator.compare_repo())
            elif "linux" in sys.platform.lower():
                os.system("xdg-open " + comparator.compare_repo())
            else:
                print "\n>> Comparision complete. Check the 'reports.htm' file in your reports folder."
        elif command.lower() == "e":
            break
        elif command.lower() == "n":
            comparator.update_nodes_list()
        elif command.lower() == "help":
            print """
n - rebuild nodes list from file specified as nodes_list in config.ini
r - copy files from nodes list to repository
c - compare files in repository with the files from nodes list
e - exit
"""
        else:
            print "\n>> Invalid command. Please, make your choice. \n "
