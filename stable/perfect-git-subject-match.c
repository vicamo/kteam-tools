#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_LINE 1024
static char line[MAX_LINE];

void main(int argc, char *argv[])
{
	if (argc != 2) {
		fprintf(stderr, "Too many arguments.\n");
		exit(1);
	}

	while (fgets(line, MAX_LINE, stdin))
	{
		int len;
		char *sha1, *subject;
		char *nl = strchr(line, '\n');
		if (nl)
			*nl = '\0';

		len = strlen(line);
		sha1 = line;
		subject = strchr(line, ' ');
		if (subject) {
			*subject = '\0';
			subject++;
		}
		else
			continue;
			
		if (subject-line >= len)
			continue;

		if ((strlen(argv[1]) == strlen(subject)) && (!strcmp(subject,argv[1])))
			printf("%s %s\n",sha1,subject);
	}
}

