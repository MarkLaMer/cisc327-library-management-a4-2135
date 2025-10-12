#include <stdio.h>
#include <unistd.h>
#include <sys/wait.h>

int main() {
    int i;

    for (i = 0; i < 3; i++) {
        fork();
    }

    /* After fork(), there are two processes, 
    the parent and the child, and both continue execution 
    from the next line after the fork() call */
    
    static int count = 0;
    count++;
    printf("Process %d reporting in! PID=%d, PPID=%d\n", count, getpid(), getppid());

    return 0;
}