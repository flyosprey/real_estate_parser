function main(splash, args)
    splash.js_enabled = true
    splash:on_request(function(request)
        request.dont_filter = true
    end)
    splash:go{args.url, headers=args.headers}
    splash:wait(args.wait)
    return {
        html = splash:html(),
    }
end