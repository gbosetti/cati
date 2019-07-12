require 'date'

def register(params)

end


def filter(event)
    logger.info("1")
    r = event.get('text').gsub(/\[do\/?[^>]*\]/,'')
    logger.info("2")
    event.set('text',r)
    logger.info("3")
    return [event]
end
