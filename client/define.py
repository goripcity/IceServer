#coding=utf-8

from ctypes import *

NULLPTR = POINTER(c_int)()


###### libc #######



class Timeval(Structure):
    _fields_ = [("tv_sec", c_long),
                ("suseconds_t", c_long)]




##### redis #######

"""

/* This is the reply object returned by redisCommand() */
typedef struct redisReply {
    int type; /* REDIS_REPLY_* */
    long long integer; /* The integer when type is REDIS_REPLY_INTEGER */
    int len; /* Length of string */
    char *str; /* Used for both REDIS_REPLY_ERROR and REDIS_REPLY_STRING */
    size_t elements; /* number of elements, for REDIS_REPLY_ARRAY */
    struct redisReply **element; /* elements vector for REDIS_REPLY_ARRAY */
} redisReply;

"""


class redisReply(Structure):
    pass

redisReply._fields_ = [("type", c_int),
                       ("integer", c_longlong),
                       ("len", c_int),
                       ("str", c_char_p),
                       ("elements", c_size_t),
                       ("element", POINTER(POINTER(redisReply)))]



"""

typedef struct redisReadTask {
    int type;
    int elements; /* number of elements in multibulk container */
    int idx; /* index in parent (array) object */
    void *obj; /* holds user-generated value for a read task */
    struct redisReadTask *parent; /* parent task */
    void *privdata; /* user-settable arbitrary field */
} redisReadTask;

"""


class redisReadTask(Structure):
    pass

redisReadTask._fields_ = [("type", c_int),
                          ("elements", c_int),
                          ("idx", c_int),
                          ("obj", c_void_p),
                          ("parent", POINTER(redisReadTask)),
                          ("privdata", c_void_p)]



"""

typedef struct redisReplyObjectFunctions {
    void *(*createString)(const redisReadTask*, char*, size_t);
    void *(*createArray)(const redisReadTask*, int);
    void *(*createInteger)(const redisReadTask*, long long);
    void *(*createNil)(const redisReadTask*);
    void (*freeObject)(void*);
} redisReplyObjectFunctions;

"""



class redisReplyObjectFunctions(Structure):
    _fields_ = [("createString", c_void_p),
                ("createArray", c_void_p),
                ("createInteger", c_void_p),
                ("createNil", c_void_p),
                ("freeObject", c_void_p)]
                


"""

/* State for the protocol parser */
typedef struct redisReader {
    int err; /* Error flags, 0 when there is no error */
    char errstr[128]; /* String representation of error when applicable */

    char *buf; /* Read buffer */
    size_t pos; /* Buffer cursor */
    size_t len; /* Buffer length */
    size_t maxbuf; /* Max length of unused buffer */

    redisReadTask rstack[9];
    int ridx; /* Index of current read task */
    void *reply; /* Temporary reply pointer */

    redisReplyObjectFunctions *fn;
    void *privdata;
} redisReader;

"""



class redisReader(Structure):
    _fields_ = [("err", c_int),
                ("errstr", c_char * 128),
                ("buf", c_char_p),
                ("pos", c_size_t),
                ("len", c_size_t),
                ("maxbuf", c_size_t),
                ("redisReadTask", redisReadTask * 9),
                ("ridx", c_int),
                ("reply", c_void_p),
                ("fn", POINTER(redisReplyObjectFunctions)),
                ("privdata", c_void_p)]
                


"""

/* Context for a connection to Redis */
typedef struct redisContext {
    int err; /* Error flags, 0 when there is no error */
    char errstr[128]; /* String representation of error when applicable */
    int fd;
    int flags;
    char *obuf; /* Write buffer */
    redisReader *reader; /* Protocol reader */
} redisContext;

"""


class redisContext(Structure):
    _fields_ = [("err", c_int),
                ("errstr", c_char * 128),
                ("fd", c_int),
                ("flags", c_int),
                ("obuf", c_char_p),
                ("reader", POINTER(redisReader))]
                        

"""

typedef struct redisCallback {
    struct redisCallback *next; /* simple singly linked list */
    redisCallbackFn *fn;
    void *privdata;
} redisCallback;

"""



class redisCallback(Structure):
    pass

redisCallback._fields_ = [("next", POINTER(redisCallback)),
                          ("fn", c_void_p),
                          ("privdata", c_void_p)]



"""

/* List of callbacks for either regular replies or pub/sub */
typedef struct redisCallbackList {
    redisCallback *head, *tail;
} redisCallbackList;

"""



class redisCallbackList(Structure):
    _fields_ = [("head", POINTER(redisCallback)),
                ("tail", POINTER(redisCallback))]



"""

/* Context for an async connection to Redis */
typedef struct redisAsyncContext {
    /* Hold the regular context, so it can be realloc'ed. */
    redisContext c;

    /* Setup error flags so they can be used directly. */
    int err;
    char *errstr;

    /* Not used by hiredis */
    void *data;

    /* Event library data and hooks */
    struct {
        void *data;

        /* Hooks that are called when the library expects to start
         * reading/writing. These functions should be idempotent. */
        void (*addRead)(void *privdata);
        void (*delRead)(void *privdata);
        void (*addWrite)(void *privdata);
        void (*delWrite)(void *privdata);
        void (*cleanup)(void *privdata);
      } ev;

    /* Called when either the connection is terminated due to an error or per
     * user request. The status is set accordingly (REDIS_OK, REDIS_ERR). */
    redisDisconnectCallback *onDisconnect;

    /* Called when the first write event was received. */
    redisConnectCallback *onConnect;

    /* Regular command callbacks */
    redisCallbackList replies;

    /* Subscription callbacks */
    struct {
        redisCallbackList invalid;
        struct dict *channels;
        struct dict *patterns;
    } sub;
} redisAsyncContext;
 

"""


class redisSub(Structure):
    _fields_ = [("invalid", redisCallbackList),
                ("channels", c_void_p),    #ignore dict struct 
                ("patterns", c_void_p)]    #ignore dict struct





EVFUNC = CFUNCTYPE(None, c_void_p)

class redisEvent(Structure):
    _fields_ = [("data", c_void_p),
                ("addRead", EVFUNC),
                ("delRead", EVFUNC),
                ("addWrite", EVFUNC),
                ("delWrite", EVFUNC),
                ("cleanup", EVFUNC)]




class redisAsyncContext(Structure):
    _fields_ = [("c", redisContext), 
                ("err", c_int),
                ("errstr", c_char_p),
                ("data", c_void_p),
                ("ev", redisEvent),
                ("onDisconnect", c_void_p),
                ("onConnect", c_void_p),
                ("replies", redisCallbackList),
                ("sub", redisSub)] 
                                            

