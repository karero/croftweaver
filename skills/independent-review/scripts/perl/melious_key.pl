# The key from a Melious env file (melious_key): the first MELIOUS_API_KEY= line of the file named as
# the argument, `export ` prefix allowed; trailing whitespace (a CRLF ending included) and one pair of
# surrounding quotes dropped. Parsed, never sourced. Prints the key, or nothing.
use 5.010;

while (<>) {
  if (s/^(?:export[ \t]+)?MELIOUS_API_KEY=//) { s/\s+\z//; s/^"(.*)"\z/$1/ or s/^\x27(.*)\x27\z/$1/; print; exit }
}
