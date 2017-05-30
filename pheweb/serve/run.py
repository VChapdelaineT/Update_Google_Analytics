
def run_flask_dev_server(app, args):
    app.run(
        host=args.host, port=args.port,
        debug=True, use_evalex=False,
        use_reloader=args.use_reloader,
    )

def run_gunicorn(app, args):
    import gunicorn.app.base
    class StandaloneGunicornApplication(gunicorn.app.base.BaseApplication):
        # from <http://docs.gunicorn.org/en/stable/custom.html>
        def __init__(self, app, opts=None):
            self.application = app
            self.options = opts or {}
            super().__init__()
        def load_config(self):
            for key, val in self.options.items():
                self.cfg.set(key, val)
        def load(self):
            return self.application

    options = {
        'bind': '{}:{}'.format(args.host, args.port),
        'reload': args.use_reloader,
        'workers': args.num_workers,
        'accesslog': '-',
        'access_log_format': '%(t)s | %(s)s | %(L)ss | %(m)s %(U)s | resp_len:%(B)s | referrer:"%(f)s" | from:%(h)s',
        # docs @ <http://docs.gunicorn.org/en/stable/settings.html#access-log-format>
    })
    sga = StandaloneGunicornApplication(app, options)
    # for skey,sval in sorted(sga.cfg.settings.items()):
    #     cli_args = sval.cli and ' '.join(sval.cli) or ''
    #     val = str(sval.value)
    #     print(f'cfg.{skey:25} {cli_args:28} {val}')
    #     if sval.value != sval.default:
    #         print(f'             default: {str(sval.default)}')
    #         print(f'             short: {sval.short}')
    #         print(f'             desc: <<\n{sval.desc}\n>>')
    sga.run()

def gunicorn_is_broken():
    try:
        import gunicorn.app.base
    except:
        try:
            import inotify
        except ImportError:
            raise
        else:
            # `import gunicorn` is failing because `inotify` is installed.
            # see <https://github.com/benoitc/gunicorn/issues/1477>
            print("On python3 gunicorn is incompatible with inotify, so PheWeb will use the less-secure, slower Flask development server while inotify is installed.\n")
            return True
    return False

def print_ip(port):
    ip = get_ip()
    print('If you can open a web browser on this computer (ie, the one running PheWeb), open http://localhost:{} .'.format(port))
    print('')
    print('If not, maybe http://{}:{} will work.'.format(ip, port))
    print("If that link doesn't work, it's either because:")
    print("  - the IP {} is failing to route to this computer (eg, this computer is inside a NAT), or".format(ip))
    print("  - a firewall is blocking port {}.".format(port))
    print('')

def get_ip():
    import subprocess
    return subprocess.check_output('dig +short myip.opendns.com @resolver1.opendns.com'.split()).strip().decode('ascii')
    # import socket
    # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # sock.connect(('resolver1.opendns.com', 53))
    # sock.send(b'\0\0\1\0\0\1\0\0\0\0\0\0\4myip\7opendns\3com\0\0\1\0\1')
    # resp = sock.recv(1000)
    # return '.'.join(str(b) for b in resp[-4:])
    # import requests, re
    # data = requests.get('http://checkip.dyndns.com/').text
    # return re.compile(r'Address: (\d+\.\d+\.\d+\.\d+)').search(data).group(1)

def attempt_open(url):
    import os
    import webbrowser
    if 'DISPLAY' not in os.environ:
        print('The DISPLAY variable is not set, so not attempting to open a web browser\n')
        return False
    for name in 'windows-default chrome chromium mozilla firefox opera safari'.split():
        # LATER: prepend `macosx` to this list when <http://bugs.python.org/issue30392> is fixed.
        try:
            b = webbrowser.get(name)
        except:
            pass
        else:
            if b.open(url):
                return True
    return False


def run(argv):

    from .server import app

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0', help='the hostname to use to access this server')
    parser.add_argument('--port', type=int, default=5000, help='an integer for the accumulator')
    parser.add_argument('--no-reloader', action='store_false', dest='use_reloader')
    parser.add_argument('--num-workers', type=int, default=4, help='number of worker threads')
    parser.add_argument('--guess-address', action='store_true', help='guess the IP address')
    parser.add_argument('--open', action='store_true', help='try to open a web browser')
    args = parser.parse_args(argv)

    if args.open:
        if not attempt_open('http://localhost:{}'.format(args.port)) and not args.guess_address:
            print_ip(args.port)

    if args.guess_address:
        print_ip(args.port)

    if gunicorn_is_broken():
        run_flask_dev_server(app, args)
    else:
        run_gunicorn(app, args)
