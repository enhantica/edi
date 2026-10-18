/* Test-only exact owned-path IO interval and passive bytes. No classifier answers. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <limits.h>
static __thread int busy;
static _Atomic int phase;
/* Every live original descriptor keeps its own immutable object obligation.
 * Capacity/identity/lost-channel failures terminate this TEST fixture loudly. */
#define OBSERVED_FDS 64
#define OBSERVED_OBJECTS 8
struct observed_fd {int active,fd;unsigned long long dev,ino;};
struct observed_object {unsigned long long dev,ino;};
static struct observed_fd observed[OBSERVED_FDS];
static struct observed_object objects[OBSERVED_OBJECTS];
static _Atomic unsigned object_count;
static pthread_mutex_t observer_lock=PTHREAD_MUTEX_INITIALIZER;
static void observer_fail(void){
 const char message[]="INPUT414 observer witness unavailable; no read-safety PASS\n";
 syscall(SYS_write,STDERR_FILENO,message,sizeof(message)-1);_exit(121);
}
static int slot_for(int fd){for(int i=0;i<OBSERVED_FDS;i++)if(observed[i].active&&observed[i].fd==fd)return i;return -1;}
static int same_object(const struct stat*s,const struct observed_fd*entry){return (unsigned long long)s->st_dev==entry->dev&&(unsigned long long)s->st_ino==entry->ino;}
static int seen_object(const struct stat*s){for(unsigned i=0;i<object_count;i++)if(objects[i].dev==(unsigned long long)s->st_dev&&objects[i].ino==(unsigned long long)s->st_ino)return 1;return 0;}
static void track(int fd){
 struct stat s;if(fstat(fd,&s)||!S_ISREG(s.st_mode)||slot_for(fd)>=0)observer_fail();
 int free_slot=-1;for(int i=0;i<OBSERVED_FDS;i++)if(!observed[i].active){free_slot=i;break;}
 if(free_slot<0)observer_fail();
 if(!seen_object(&s)){unsigned n=object_count;if(n>=OBSERVED_OBJECTS)observer_fail();objects[n]=(struct observed_object){s.st_dev,s.st_ino};object_count=n+1;}
 observed[free_slot]=(struct observed_fd){1,fd,s.st_dev,s.st_ino};
}
static int armed(void){const char*p=getenv("EDI_INPUT410_ARM");struct stat s;return p&&syscall(SYS_newfstatat,AT_FDCWD,p,&s,0)==0;}
static int match(const char*p){const char*t=getenv("EDI_INPUT410_TARGET");return !busy&&p&&t&&!strcmp(p,t)&&armed();}
static void receipt(const char*event,int fd,const char*path){
 const char*log=getenv("EDI_INPUT410_LOG");if(!log)observer_fail();
 struct stat s={0};char actual[PATH_MAX]={0},proc[64],line[PATH_MAX*2+256];
 if(fd>=0){if(fstat(fd,&s))observer_fail();snprintf(proc,sizeof(proc),"/proc/self/fd/%d",fd);ssize_t n=readlink(proc,actual,sizeof(actual)-1);if(n<0)observer_fail();actual[n]=0;}
 int n=snprintf(line,sizeof(line),"%s\t%d\t%d\t%llu\t%llu\t%s\t%s\n",event,phase,fd,(unsigned long long)s.st_dev,(unsigned long long)s.st_ino,path?path:"",actual);
 int out=syscall(SYS_openat,AT_FDCWD,log,O_WRONLY|O_CREAT|O_APPEND|O_CLOEXEC,0600);
 if(out<0||n<=0||(size_t)n>=sizeof(line))observer_fail();
 ssize_t written=syscall(SYS_write,out,line,n);if(syscall(SYS_close,out)||written!=n)observer_fail();
}
static int swap(const char*variable){
 const char*p=getenv("EDI_INPUT410_SWAP"),*to=getenv(variable);char next[PATH_MAX];
 if(!p||!to||snprintf(next,sizeof(next),"%s.input410-next",p)>=(int)sizeof(next))return 0;
 unlink(next);if(symlink(to,next)!=0)return 0;if(rename(next,p)!=0){unlink(next);return 0;}return 1;
}
static int needs_mode(int flags){return (flags&O_CREAT)||((flags&O_TMPFILE)==O_TMPFILE);}
static int before_open(const char*path,int flags){
 if(!match(path)||(flags&(O_WRONLY|O_RDWR|O_CREAT|O_PATH))||((flags&O_TMPFILE)==O_TMPFILE))return 0;
 const char*edge=getenv("EDI_INPUT410_EDGE");int expected=0;
 if(!edge||(strcmp(edge,"source")&&strcmp(edge,"selected"))||!atomic_compare_exchange_strong(&phase,&expected,1))return 0;
 int saved=errno;busy=1;receipt(swap("EDI_INPUT410_SWITCH_TO")?"before-open-A":"switch-error",-1,path);busy=0;errno=saved;return 1;
}
static void after_open(const char*path,int flags,int fd,int changed){
 if(busy)return;
 const int targeted=match(path);if(!targeted&&!object_count)return;
 int saved=errno;busy=1;if(pthread_mutex_lock(&observer_lock)){observer_fail();}
 /* A successful open cannot reuse a still-live descriptor. An unobserved raw
  * close/reuse is an unsupported witness, never silently overwritten. */
 if(fd>=0&&slot_for(fd)>=0)observer_fail();
 if(targeted&&fd>=0&&!(flags&(O_WRONLY|O_RDWR|O_CREAT|O_PATH))&&((flags&O_TMPFILE)!=O_TMPFILE)){
  track(fd);receipt("opened",fd,path);
 }
 if(targeted&&changed){receipt(swap("EDI_INPUT410_RESTORE_TO")?"alias-restored":"switch-error",fd,path);phase=2;}
 if(pthread_mutex_unlock(&observer_lock)){observer_fail();}busy=0;errno=saved;
}
int open(const char*path,int flags,...){
 mode_t mode=0;if(needs_mode(flags)){va_list a;va_start(a,flags);mode=va_arg(a,int);va_end(a);}
 int(*real)(const char*,int,...)=dlsym(RTLD_NEXT,"open");int changed=before_open(path,flags),fd=real(path,flags,mode);after_open(path,flags,fd,changed);return fd;
}
int open64(const char*path,int flags,...){
 mode_t mode=0;if(needs_mode(flags)){va_list a;va_start(a,flags);mode=va_arg(a,int);va_end(a);}
 int(*real)(const char*,int,...)=dlsym(RTLD_NEXT,"open64");int changed=before_open(path,flags),fd=real(path,flags,mode);after_open(path,flags,fd,changed);return fd;
}
int openat(int dir,const char*path,int flags,...){
 mode_t mode=0;if(needs_mode(flags)){va_list a;va_start(a,flags);mode=va_arg(a,int);va_end(a);}
 int(*real)(int,const char*,int,...)=dlsym(RTLD_NEXT,"openat");int changed=before_open(path,flags),fd=real(dir,path,flags,mode);after_open(path,flags,fd,changed);return fd;
}
char*realpath(const char*path,char*out){
 char*(*real)(const char*,char*)=dlsym(RTLD_NEXT,"realpath");char*value=real(path,out);
 if(match(path)){int saved=errno;busy=1;receipt("canonical",-1,value);busy=0;errno=saved;}return value;
}
int close(int fd){
 int(*real)(int)=dlsym(RTLD_NEXT,"close");
 if(busy||!object_count)return real(fd);
 int saved=errno;busy=1;if(pthread_mutex_lock(&observer_lock)){observer_fail();}int slot=slot_for(fd);
 if(slot<0){if(pthread_mutex_unlock(&observer_lock)){observer_fail();}busy=0;errno=saved;return real(fd);}
 struct stat before;if(fstat(fd,&before)||!same_object(&before,&observed[slot]))observer_fail();
 receipt("close-request",fd,"");errno=saved;int result=real(fd);saved=errno;
 if(result){observer_fail();}
 observed[slot].active=0;
 if(pthread_mutex_unlock(&observer_lock)){observer_fail();}busy=0;errno=saved;return result;
}
ssize_t read(int fd,void*buffer,size_t count){
 ssize_t(*real)(int,void*,size_t)=dlsym(RTLD_NEXT,"read");
 if(busy||!object_count)return real(fd,buffer,count);
 int saved=errno;busy=1;if(pthread_mutex_lock(&observer_lock)){observer_fail();}int slot=slot_for(fd);struct stat before;
 if(slot<0){
  /* An unobserved dup/fcntl/direct-syscall route to an original object is not
   * absence of a protected read. Refuse the witness before returning bytes. */
  if(!fstat(fd,&before)&&seen_object(&before))observer_fail();
  if(pthread_mutex_unlock(&observer_lock)){observer_fail();}busy=0;errno=saved;return real(fd,buffer,count);
 }
 if(fstat(fd,&before)||!same_object(&before,&observed[slot]))observer_fail();
 off_t offset=lseek(fd,0,SEEK_CUR);if(offset<0)observer_fail();
 errno=saved;ssize_t n=real(fd,buffer,count);saved=errno;struct stat after;
 if(fstat(fd,&after)||!same_object(&after,&observed[slot]))observer_fail();
 if(n>0){
  if(n>512)observer_fail();
  char hex[1060];int start=snprintf(hex,sizeof(hex),"%lld:",(long long)offset);
  for(ssize_t i=0;i<n;i++)snprintf(hex+start+i*2,3,"%02x",((unsigned char*)buffer)[i]);
  receipt("read-bytes",fd,hex);
 }
 if(pthread_mutex_unlock(&observer_lock)){observer_fail();}busy=0;errno=saved;return n;
}
