require 'date'

def register(params)

end


def filter(event)
    r = event.get('text').gsub(/\[do\/?[^>]*\]/,'')
    event.set('text',r)
    return [event]
end