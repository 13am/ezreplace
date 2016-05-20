# ezreplace

DESCRIPTION

Use ezreplace.py to replace words in input. Input and output may be from files or a streams.

Examples:

A. Read the file "doc.txt" line by line. Write each line to "nice_doc.txt" while replacing words 
listed in the file "nice_words.txt", which contains lines of form "old_word new_word".

> ezreplace.py --in doc.txt --replacements nice_words.txt --out nicer_doc.txt

B. As above but now assume the file is divided into columns and only replace the words in the
3rd column counting from left and leave words in other column as they were.

> ezreplace.py --column 3 --in doc.txt --replacements nice_words.txt --out nicer_doc.txt

C. Read input from STDIN and write output to STDOUT.

> gunzip -c doc.txt.gz | ezreplace.py --replacements nice_words.txt --stdout | gzip -c > nicer_doc.txt.gz

REQUIREMENTS

Python 2.7 or newer.


INSTALLATION

Copy the file ezreplace.py to a folder. To execute, type:
python path/to/ezprelace.py --help

