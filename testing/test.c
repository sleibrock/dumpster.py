/*
  This is a test program to output all C constants for inotify
  as well as create an inotify instance. Finding these constants
  is very annoying at times.
*/

#include <stdio.h>
#include <errno.h> 
#include <string.h>
#include <unistd.h>
#include <sys/inotify.h>

int main() {
    // test all C defined constants for inotify
    printf("\n\nTesting the constants code\n");
    printf("IN_ACCESS %x\n", IN_ACCESS);
    printf("IN_MODIFY %x\n", IN_MODIFY);
    printf("IN_ATTRIB %x\n", IN_ATTRIB);
    printf("IN_CLOSE_WRITE %x\n", IN_CLOSE_WRITE);
    printf("IN_CLOSE_NOWRITE %x\n", IN_CLOSE_NOWRITE);
    printf("IN_OPEN %x\n", IN_OPEN);
    printf("IN_MOVED_FROM %x\n", IN_MOVED_FROM);
    printf("IN_MOVED_TO %x\n", IN_MOVED_TO);
    printf("IN_CREATE %x\n", IN_CREATE);
    printf("IN_DELETE %x\n", IN_DELETE);
    printf("IN_DELETE_SELF %x\n", IN_DELETE_SELF);
    printf("IN_MOVE_SELF %x\n", IN_MOVE_SELF);
    printf("IN_ISDIR %x\n", IN_ISDIR);
    printf("IN_UNMOUNT %x\n", IN_UNMOUNT);
    printf("IN_Q_OVERFLOW %x\n", IN_Q_OVERFLOW);
    printf("IN_CLOEXEC %x\n", IN_CLOEXEC);
    printf("IN_NONBLOCK %x\n", IN_NONBLOCK);
    printf("Done\n\n");

    // make an inotify instance
    int inotify_fd;
    inotify_fd = inotify_init1(IN_NONBLOCK);

    if (inotify_fd == -1) {
        // Immediately check errno
        int err = errno;
        fprintf(stderr, "inotify_init1 returned -1\n");
        fprintf(stderr, "error: %d (%s)", err, strerror(err));
        return 1; // Indicate failure
    } else {
        printf("inotify_init1 returned  %d\n", inotify_fd);
        close(inotify_fd); // Clean up
        printf("FD closed.\n");
        return 0; // Indicate success
    }
}
