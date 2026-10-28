/* Independent actual-file persistence witness. Pattern: temporary_failure.c.
 * Only an explicitly armed run-owned canonical file/directory can be affected. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>
#include <limits.h>
#include <stdatomic.h>
#ifdef __APPLE__
#include <pthread.h>
#include <stdint.h>
#endif
#ifdef __linux__
#include <sys/syscall.h>
#endif
#include "../project_output/fault_interpose.h"
struct control {char mode[16], target[PATH_MAX], release[PATH_MAX];unsigned epoch;};
static _Thread_local int inside;
static _Atomic unsigned serial;
static int read_control(struct control *out) {
 const char *name=getenv("EDI_TEST_HISTORY_CONTROL");
 if(!name || inside)return 0;
 int fd=open(name,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);if(fd<0)return 0;
 char buffer[PATH_MAX*2+128];ssize_t n=read(fd,buffer,sizeof(buffer)-1);close(fd);
 if(n<=0)return 0;
 buffer[n]=0;
 char *save=0,*mode=strtok_r(buffer,"\n",&save),*target=strtok_r(0,"\n",&save),*release=strtok_r(0,"\n",&save),*epoch=strtok_r(0,"\n",&save);
 if(!mode || !target || !release || !epoch || strlen(mode)>=sizeof(out->mode) || strlen(target)>=sizeof(out->target) || strlen(release)>=sizeof(out->release) || target[0]!='/' || release[0]!='/')return 0;
 strcpy(out->mode,mode);strcpy(out->target,target);strcpy(out->release,release);out->epoch=(unsigned)strtoul(epoch,0,10);
 return !strcmp(mode,"hold") || !strcmp(mode,"fail");
}
static void receipt(const char *phase,const char *operation,const struct control *c,unsigned number) {
 const char *name=getenv("EDI_TEST_HISTORY_RECEIPT");if(!name)return;
 int fd=open(name,O_CREAT|O_WRONLY|O_APPEND|O_CLOEXEC|O_NOFOLLOW,0600);if(fd<0)return;
 long tid=(long)getpid();int main_thread=1;
#ifdef __linux__
 tid=(long)syscall(SYS_gettid);main_thread=tid==(long)getpid();
#elif defined(__APPLE__)
 uint64_t native_tid=0;pthread_threadid_np(0,&native_tid);tid=(long)native_tid;main_thread=pthread_main_np();
#endif
 char row[512];int n=snprintf(row,sizeof(row),"{\"phase\":\"%s\",\"operation\":\"%s\",\"epoch\":%u,\"serial\":%u,\"pid\":%ld,\"tid\":%ld,\"main_thread\":%d,\"mode\":\"%s\"}\n",phase,operation,c->epoch,number,(long)getpid(),tid,main_thread,c->mode);
 if(n>0 && n<(int)sizeof(row))(void)write(fd,row,(size_t)n);
 close(fd);
}
static int selected_fd(int fd,const char *target) {
 struct stat st;if(fstat(fd,&st) || !S_ISREG(st.st_mode) || st.st_uid!=geteuid())return 0;
 char actual[PATH_MAX];
#ifdef __linux__
 char link[64];snprintf(link,sizeof(link),"/proc/self/fd/%d",fd);ssize_t n=readlink(link,actual,sizeof(actual)-1);if(n<0)return 0;actual[n]=0;
#elif defined(__APPLE__)
 if(fcntl(fd,F_GETPATH,actual)<0)return 0;
#else
 return 0;
#endif
 const char *slash=strrchr(target,'/');if(!slash)return 0;size_t parent=(size_t)(slash-target);
 return !strncmp(actual,target,parent) && actual[parent]=='/' && !strchr(actual+parent+1,'/');
}
static unsigned hold_sync(int fd,const char *operation,struct control *captured) {
 struct control c;if(!read_control(&c) || strcmp(c.mode,"hold") || !selected_fd(fd,c.target))return 0;
 *captured=c;inside=1;unsigned number=atomic_fetch_add(&serial,1)+1;receipt("entered",operation,&c,number);
 struct timespec begin,now,pause={0,1000000};clock_gettime(CLOCK_MONOTONIC,&begin);
 while(access(c.release,F_OK)) {
  clock_gettime(CLOCK_MONOTONIC,&now);
  if(now.tv_sec-begin.tv_sec>=15){receipt("auto_release",operation,&c,number);inside=0;return number;}
  nanosleep(&pause,0);
 }
 receipt("released",operation,&c,number);inside=0;return number;
}
int FAULT(fsync)(int fd) {int (*original)(int)=REAL(fsync);struct control c;unsigned n=hold_sync(fd,"fsync",&c);int result=original(fd),error=errno;if(n)receipt(result?"sync_failed":"sync_returned","fsync",&c,n);errno=error;return result;}
INTERPOSE(fsync)
#ifdef __linux__
int FAULT(fdatasync)(int fd) {int (*original)(int)=REAL(fdatasync);struct control c;unsigned n=hold_sync(fd,"fdatasync",&c);int result=original(fd),error=errno;if(n)receipt(result?"sync_failed":"sync_returned","fdatasync",&c,n);errno=error;return result;}
INTERPOSE(fdatasync)
#endif
int FAULT(rename)(const char *from,const char *to) {
 int (*original)(const char*,const char*)=REAL(rename);struct control c;
 if(read_control(&c) && !strcmp(c.mode,"fail") && !strcmp(c.target,to)) {
  inside=1;receipt("failed","rename",&c,atomic_fetch_add(&serial,1)+1);inside=0;errno=EACCES;return -1;
 }
 return original(from,to);
}
INTERPOSE(rename)
