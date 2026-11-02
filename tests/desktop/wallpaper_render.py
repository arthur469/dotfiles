"""Actual libmpv software rendering into memory; no display, IPC or user media."""
import ctypes as C
import ctypes.util
import shlex
import time

class Param(C.Structure):
    _fields_ = [('type', C.c_int), ('data', C.c_void_p)]

def render_edges(options, image, sizes):
    library = ctypes.util.find_library('mpv')
    if not library:
        raise RuntimeError('libmpv is required for wallpaper rendering regression')
    mpv = C.CDLL(library)
    signatures = {
        'mpv_create': ([], C.c_void_p),
        'mpv_set_option_string': ([C.c_void_p,C.c_char_p,C.c_char_p],C.c_int),
        'mpv_initialize': ([C.c_void_p],C.c_int),
        'mpv_command': ([C.c_void_p,C.POINTER(C.c_char_p)],C.c_int),
        'mpv_wait_event': ([C.c_void_p,C.c_double],C.c_void_p),
        'mpv_get_property_string': ([C.c_void_p,C.c_char_p],C.c_void_p),
        'mpv_free': ([C.c_void_p],None),
        'mpv_render_context_create': ([C.POINTER(C.c_void_p),C.c_void_p,C.POINTER(Param)],C.c_int),
        'mpv_render_context_update': ([C.c_void_p],C.c_uint64),
        'mpv_render_context_render': ([C.c_void_p,C.POINTER(Param)],C.c_int),
        'mpv_render_context_free': ([C.c_void_p],None),
        'mpv_terminate_destroy': ([C.c_void_p],None),
    }
    for name,(args,result) in signatures.items():
        function=getattr(mpv,name);function.argtypes=args;function.restype=result
    handle=mpv.mpv_create()
    if not handle:raise RuntimeError('mpv_create failed')
    context=C.c_void_p()
    def check(result):
        if result<0:raise RuntimeError('libmpv error '+str(result))
    try:
        settings={'config':'no','terminal':'no','msg-level':'all=no','vo':'libmpv',
                  'audio':'no','hwdec':'no','pause':'yes','image-display-duration':'inf'}
        # Take layout options from the real production launch. IPC/script and
        # visibility controls are tested separately; they never run in this VO.
        for token in shlex.split(options):
            key,_,value=token.partition('=')
            if key in {'panscan','keepaspect','video-zoom','video-unscaled',
                       'video-pan-x','video-pan-y','video-align-x','video-align-y'}:
                settings[key]=value
        for key,value in settings.items():check(mpv.mpv_set_option_string(handle,key.encode(),value.encode()))
        check(mpv.mpv_initialize(handle))
        aspect=mpv.mpv_get_property_string(handle,b'keepaspect')
        if not aspect:raise RuntimeError('Cannot read keepaspect')
        try:
            if C.string_at(aspect)!=b'yes':raise AssertionError('Wallpaper must preserve aspect ratio')
        finally:mpv.mpv_free(aspect)
        api=C.create_string_buffer(b'sw')
        check(mpv.mpv_render_context_create(C.byref(context),handle,(Param*2)(Param(1,C.cast(api,C.c_void_p)),Param(0,None))))
        check(mpv.mpv_command(handle,(C.c_char_p*3)(b'loadfile',str(image).encode(),None)))
        result=[]
        for width,height in sizes:
            size=(C.c_int*2)(width,height);stride=C.c_size_t(((width*4+63)//64)*64)
            raw=C.create_string_buffer(stride.value*height+63)
            address=(C.addressof(raw)+63)&~63
            pixels=(C.c_ubyte*(stride.value*height)).from_address(address)
            fmt=C.create_string_buffer(b'rgb0')
            params=(Param*5)(Param(17,C.cast(size,C.c_void_p)),Param(18,C.cast(fmt,C.c_void_p)),Param(19,C.cast(C.byref(stride),C.c_void_p)),Param(20,address),Param(0,None))
            def pixel(x,y):
                offset=y*stride.value+x*4;return tuple(pixels[offset:offset+3])
            deadline=time.monotonic()+3
            while True:
                mpv.mpv_wait_event(handle,0)
                mpv.mpv_render_context_update(context)
                check(mpv.mpv_render_context_render(context,params))
                if pixel(width//2,height//2)[1]>80:break
                if time.monotonic()>deadline:raise RuntimeError('No fixture frame rendered')
                time.sleep(.005)
            # Render once more at the target size after the initial frame.
            check(mpv.mpv_render_context_render(context,params))
            points=[(1,1),(width-2,1),(1,height-2),(width-2,height-2),
                    (1,height//2),(width-2,height//2),(width//2,1),(width//2,height-2)]
            result.append({'size':(width,height),'edges':[pixel(x,y) for x,y in points]})
        return result
    finally:
        if context:mpv.mpv_render_context_free(context)
        mpv.mpv_terminate_destroy(handle)
