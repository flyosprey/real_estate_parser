function main(splash, args)
    splash.js_enabled = true
    assert(splash:go(args.url, headers=splash.args.headers))
    assert(splash:wait(15))
    return {
        html = splash:html(),
    }
end