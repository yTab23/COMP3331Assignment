CC = gcc
CPPFLAGS += -DCJSON_NESTING_LIMIT=64
CFLAGS = -std=c17 -Wall -Wextra -Wpedantic -O2
LDLIBS += -lm -pthread

COMMON = starter.c support/c/student_tools.c support/c/vendor/cJSON.c
HEADERS = starter.h support/c/student_tools.h support/c/vendor/cJSON.h

.PHONY: all
all: client server

client: client.c $(COMMON) $(HEADERS)
	$(CC) $(CPPFLAGS) $(CFLAGS) -pthread client.c $(COMMON) $(LDFLAGS) $(LDLIBS) -o $@

server: server.c $(COMMON) $(HEADERS)
	$(CC) $(CPPFLAGS) $(CFLAGS) -pthread server.c $(COMMON) $(LDFLAGS) $(LDLIBS) -o $@
