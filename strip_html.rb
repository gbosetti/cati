require 'date'
require 'nokogiri'

def register(params)

end


def filter(event)
    #event.set("timestamp_ms", DateTime.parse(event.get("published")).to_time.to_i)
    #event.set("timestamp_ms", DateTime.parse(event.get("published")).strftime('%Q'))
    #timestamp = DateTime.parse(event.get("published")).to_time
    original_text = event.get("text")
    doc = Nokogiri::HTML(original_text)
    doc.xpath('//text()').each do |node|
        node.content = node.content.gsub("\n","")
        node.content = " " + node.content + " "
    end

    text = doc.text

    event.set("text", text )
    return [event]
end