import shodan

from tornado.web import HTTPError


def runShodan(api, input):

    # Wrap the request in a try/ except block to catch errors
    try:
        # Lookup the host
        return {
            "host": api.host(input),
                }

    except shodan.APIError as e:
        print(f'Error: {e}')
        if e.value == 'No information available for that IP.':
            raise HTTPError(404, f"API Error: {e}", reason="API Error")
        else:
            raise HTTPError(401, f"API Error: {e}", reason="API Error")
