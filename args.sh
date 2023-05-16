
usage() {

    if [ $# -ne 0 ]; then
        echo
        echo "One or more options cannot be processed: '$@' (See below)."
        echo
    fi

    echo "Usage: $PROGNAME -s|--site [id] [options]"
    echo
    echo "Options:"
    echo
    echo "  -h, --help"
    echo "      This help text."
    echo
    echo "  -d, --debug"
    echo "      Print out debug information"
    echo
    echo "  -s, --site"
    echo "      The site to run the workflow on"
    echo
    echo "  --"
    echo "      Do not interpret any more arguments as options."
    echo
}

VALID_ARGS=$(getopt -o s:dh --long debug,site,help: -- "$@")
if [ $? -ne 0 ] || [ $# -eq 0 ]; then
    # if error in parsing args display usage
    usage $@
    exit 1
fi

SITE_ID=
DEBUG=

eval set -- "$VALID_ARGS"
while [ : ]; do
  case "$1" in
    -h|--help)
        usage
        exit 0
        ;;
    -d | --debug)
        DEBUG='-d'
        shift
        ;;
    -s | --site)
        SITE_ID=$2
        shift 2
        ;;
    --) shift;
        break
        ;;
  esac
done

if [ -z "$SITE_ID" ]; then
    usage $@
    exit 1
fi
