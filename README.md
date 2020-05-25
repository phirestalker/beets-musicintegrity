# beets-musicintegrity
A beets plugin that allows you to create par2 sets for your music files
## Installation
1. clone this repository or download a zip and expand somewhere
2. open a command prompt or terminal
3. change to the directory containing the files
4. type: python3 setup.py install
## Configuration
    par2_exe:	Set the location of your par2 executable. Tries to find it in path by default
    recovery:	Set the percentage of the recovery files (default is 15%)
	memory:		Amount of memory for par2 to use (default is 1024 MB or 1 GB)
    extra_args:	A list of other commandline options for par2 creation. Note: -q is already used
			For a list of acceptable values see: http://manpages.org/par2
			enter as a list like ['-u', '-l']
## Usage
To use this plugin you must add it to the plugins list in your config.yaml.
This plugin will automatically create a par2 set for each music file on import. It will also generate a new set for a file when it is changed by beets or other plugins. Before each file is changed it will be checked for errors and repaired. If the repair fails it will stop the operation on that file.

The plugin has four commands
* par2create: Creates a par2 set for the files given by query
* par2verify: Runs a par2 verify on files given by query (added for completeness as repair will also do a verify first)
* par2repair: Runs a par2 repair on files given by query
* par2delete: Removes all par2 sets for files returned by query
