from argparse import ArgumentParser
import sys
import tempfile
import os
import shutil

from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE,SIG_DFL) 

def parse_options():
    
    parser = ArgumentParser()
    
    parser.add_argument('--in',
                        dest='infile',
                        default=None, 
                        help='Name of the input file to be modified. Use --stdin if you want to read \
                        the input from stdin.')
    
    parser.add_argument('--out',
                        dest='out',
                        default=None, 
                        help='Name of the output file. Use --stdout if you want to write \
                        the output to stdout.')
                        
    parser.add_argument('--stdout',
                        dest='stdout',
                        default=False,
                        action="store_true",
                        help='Write output into stdout.')

    parser.add_argument('--stdin',
                        dest='stdin',
                        default=False,
                        action="store_true",
                        help='Read input from stdin.')
    
    parser.add_argument('--in-place',
                        dest='in_place',
                        default=False, 
                        action="store_true",
                        help='Save modifications in-place to the original file.')
                        
    parser.add_argument('--replacements',
                        dest='replacements',
                        default=None,
                        help='Name of the file containing (line by line) pairs of \"old new\" replacements.')
   
    parser.add_argument('--header',
                        dest='header',
                        default=False,
                        action="store_true",
                        help='Do not modify the first (header) line of the input file.')
                        
    parser.add_argument('--strip',
                        dest='strip',
                        default=False,
                        action="store_true",
                        help='Strip leading and trailing whitespace characters from the lines of the input file.')
        
    parser.add_argument('--keep-hits-only',
                        dest='keep',
                        default=False,
                        action="store_true",
                        help='Only output lines where a replacement was made. Default = False.')
    
    parser.add_argument('--column',
                        dest='column',
                        default=False,
                        help='Replace only in this specified column. The leftmost is column 1 etc.\
                        Multiple columns can be given by separating the column indexes with a comma, \
                        e.g. --column 1,2,5 would only replace in the first, second, and fifth columns and \
                        ignore matches elsewhere. If --column is not given, replacements are done as follows: \
                        1\) the targets to be replaced are sorted alpabetically \
                        2\) for each line, replacements are made in alphabetical order and replacements \
                        once made are NOT recursively replaced again. \
                        E.g.input line "dog lion cat cat tennis" \
                        with replacements "cat:tennis , tennis:football" would first replace "cat" with "tennis": \
                        "dog lion [tennis] [tennis] tennis" \
                        but only the original occurrence of "tennis" would be replaced by "football": \
                        "dog lion [tennis] [tennis] [football]" \
                        so that the final output line would be \
                        "dog lion tennis tennis football".')
 
    parser.add_argument('--sep',
                        dest='sep',
                        default=False,
                        help='Use a specific string as field delimiter. \
                        In effect only if --column also specified. \
                        If not given, ezreplace will try to guess the separator and \
                        stops if it cannot make a good guess. \
                        Possible values are "tab", "space", "whitespace", or any string \
                        such as "this script is awesome" or ";" enclosed in quotes. If you use the \
                        "whitespace" keyword as the separator, continuous stretches of any whitespace \
                        characters will be used as field separators in the input and the output will be \
                        separated by single spaces.')
        
    options = parser.parse_args()
    return options


def deduce_delimiter(lines=[], strip=False):
    space = set()
    tab = set()
    whitespace = set()
    
    for ip_line in lines:
        if strip:
            ip_line = ip_line.strip()
        tab.add(len(ip_line.split("\t")))
        space.add(len(ip_line.split(" ")))
        whitespace.add(len(ip_line.split(None)))
        
    if 1 in space:
        space.remove(1)
    if 1 in tab:
        tab.remove(1)
    if 1 in whitespace:
        whitespace.remove(1)

    if len(tab) == 1 and len(space) != 1:
        sep = "\t"
    elif len(tab) != 1 and len(space) == 1:
        sep = " "
    elif len(whitespace)  == 1:
        sep = None
    else:
        sys.stderr.write('# Field separator not explicitly given and was not \
        successfully deduced.\n')
        sys.stderr.write('# Stopping.\n')
        sys.exit()
        
    sys.stderr.write('# Field separator successfully deduced.\n')
    return sep


class Replacer:
    
    def __init__(self):
        self.exp_line_len = None
        self.linecounter = 0
        self.word_order = None
        
    def check_line_len(self, line):
        if self.exp_line_len is None:
            self.exp_line_len = len(line)
            return True
        else:
            return len(line) == self.exp_line_len
        
    def replace_line(self, kwargs, ip_line=None, is_header=False):
    
        if kwargs['strip']:
            ip_line = ip_line.strip()
            
        if kwargs['column'] is False:
            op_line = [ip_line]
            targets = [0]
            if self.word_order is None:
                self.word_order = sorted(kwargs['reps'].keys())
        else:
            op_line = ip_line.split(kwargs['sep'])
            targets = kwargs['column']
        
        if self.check_line_len(op_line) is not True:
            sys.stderr.write('# Error: the number of columns in the input is not constant.\n')
            sys.stderr.write('# Found {} columns on line {}.\n'\
                             .format(len(op_line), self.linecounter + 1 ))
            sys.stderr.write('# Expected {} columns.\n'.format(self.exp_line_len))
            sys.stderr.write('# Exit.\n')
            return False
        
        replaced = False
    
        if is_header == False or kwargs['header'] == False:
            
            # if replacing is NOT restricted to specific columns,
            # replace everywhere on the line but do not multiple
            # replacements of the same word
            if kwargs['column'] is False:
                for w in self.word_order:
                    ol = []
                    for i in op_line:
                        if type(i) != type('') or w not in i:
                            ol.append(i)
                        else:
                            for j in i.split(w):
                                ol.append(j)
                                ol.append([w])
                            ol.pop()
                    op_line = ol
                
                ol = ''
                for i in op_line:
                    if type(i) == type(''):
                        if i != '':
                            ol = ol + i
                    else:
                        replaced = True
                        kwargs['rep_counter'] += 1
                        replacement = kwargs['reps'][i[0]]
                        ol = ol + replacement
                op_line = [ol]
                        
            # if replacement is to be done in specific columns,
            # just get the replacements from the dict
            else:
                for i in targets:
                    try:
                        op_line[i] = kwargs['reps'][op_line[i]]
                        kwargs['rep_counter'] += 1
                        replaced = True
                    except KeyError:
                        kwargs['not_rep_counter'] += 1
            
            if replaced:
                kwargs['n_line_match'] += 1
            else:
                kwargs['n_line_no_match'] += 1
            
        op = kwargs['opstream']
        op_sep = kwargs['op_sep']
        
        do_write_output = is_header or kwargs['keep'] == False or replaced
        if do_write_output:
            op.write(op_sep.join(op_line))
            if kwargs['strip'] or kwargs['sep'] == None:
                op.write('\n')
                
        self.linecounter += 1
        return True


def update_delimiters(options = None, start_lines = None):
    
    # input field delimiter
    if options.column is not None:
        if options.sep == False:
            options.sep = deduce_delimiter(lines = start_lines, strip = options.strip)
        else:
            if options.sep == 'whitespace':
                options.sep = None
            else:
                if options.sep == 'space':
                    options.sep = ' '
                if options.sep == 'tab':
                    options.sep = '\t'
        
    # output field delimiter
    if options.column is None:
        options.op_sep = ''
    else:    
        if options.sep == None:
            options.op_sep = ' '
        else:
            options.op_sep = options.sep
                
    return vars(options)

class Collect:
    def __init__(self, kwargs):
        self.__dict__.update(kwargs)

def finish(success, kwargs):
    
    options = Collect(kwargs)
                
    # close streams
    if options.stdin is False:
        options.ipstream.close()
        
    if options.in_place and success:
        tmp_name = options.opstream.name
        options.opstream.close()
        info_line = "# In-place modify: replacing {} with the tmp file {}.\n"\
                    .format(options.infile, tmp_name)
        sys.stderr.write(info_line)
        try:
            os.rename(tmp_name, options.infile)
        except OSError:
            try:
                sys.stderr.write("# Using shutil.move.\n")
                shutil.move(tmp_name, options.infile)
            except:
                sys.stderr.write("# Replacement unsuccessful.\n")
    elif options.out is not None:
        options.opstream.close()
    else:
        pass
    
    # show some statistics
    if success:
        sys.stderr.write("# Replaced {} words.\n".\
                         format(kwargs['rep_counter']))
        if kwargs['column'] is not False:
            sys.stderr.write("# No replacement was found for {} words.\n"\
                             .format(kwargs['not_rep_counter']))
        sys.stderr.write("# {} lines had at least one word replaced.\n"\
                         .format(kwargs['n_line_match']))
        sys.stderr.write("# {} lines did not have any replacements made.\n"\
                         .format(kwargs['n_line_no_match']))
        sys.stderr.write("# Done.\n")
    
    sys.exit()

def main():
    
    options = parse_options()
    
    # set up the input
    if options.stdin:
        ip = sys.stdin
    elif options.infile is not None:
        ip = open(options.infile, 'r')
    else:
        sys.stderr.write('# No input specified. Use --in or --stdin.\n')
        sys.exit()
    options.ipstream = ip
        
    #set up output
    if options.in_place:
        op = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
    elif options.out is not None:
        op = open(options.out, 'w')
    elif options.stdout:
        op = sys.stdout
    else:
        sys.stderr.write('# No output specified. \
        Use one of these: --out --stdout --in-place.\n')
        sys.exit()
    options.opstream = op
                
    # parse the column notation
    if options.column is not False:
        options.column = [int(i.strip())-1 for i in options.column.split(',')]
    
    # read the replacements into a dict
    reps = {}
    with open(options.replacements, 'r') as f:
        for line in f:
            l = line.strip()
            if l != '':
                l = l.split()
                assert len(l) == 2
                reps[l[0]] = l[1]
    options.reps = reps
    info_line = "# {} replacements read from {}.\n"
    info_line = info_line.format(len(options.reps), options.replacements)
    sys.stderr.write(info_line)
                 
    options.rep_counter = 0
    options.not_rep_counter = 0
    options.n_line_match = 0
    options.n_line_no_match = 0
    replacer = Replacer()
    start_lines = []
    kwargs = {}
    
    # always read the first 666 lines into memory
    for ip_line in options.ipstream:
        if len(start_lines) < 666:
            start_lines.append(ip_line)
            if len(start_lines) == 666:
                break
        
    # check how the input looks like to define the delimiters
    kwargs = update_delimiters(options = options, start_lines = start_lines)

    # process the lines
    is_first_line = True
    for ip in (start_lines, options.ipstream):
        for line in ip:
            ok = replacer.replace_line(kwargs, ip_line = line, is_header = is_first_line)
            is_first_line = False
            if not ok:
                finish(False, kwargs)
            
    finish(True, kwargs)
            
if __name__ == '__main__':
    main()
    
