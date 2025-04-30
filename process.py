with open('others/txt.txt', 'r') as infile, open('others/output.txt', 'w') as outfile:
    lines = infile.readlines()
    outfile.write("language_codes = [\n")
    for i in range(0, len(lines), 2):
        first_line = lines[i].strip()
        second_line = lines[i + 1].strip() if i + 1 < len(lines) else ''
        outfile.write(f'"{first_line:<11}{second_line}",\n')
    outfile.write("]")