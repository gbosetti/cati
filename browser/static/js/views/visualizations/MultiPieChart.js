// gbosetti https://github.com/gbosetti
// http://jsfiddle.net/gal007/owtpzn03
class MultiPieChart{

  constructor(domSelector, width, height){

    this.domSelector = domSelector;
    this.width = width;
    this.height = height;
    this.radius = Math.min(width, height) / 2;
    this.currentBubbleWidth = 100;
  }

  createLayout(data){

  	return d3.layout
      .pack()
      .value(function(data) {
        return d3.sum(data[1]); //Proportions e.g. [100, 20, 5]
      })
      .sort(null)
      .size([this.width, this.height])
      .padding(30);
  }

  createSvg(width, height){

  	return d3
      .select(this.domSelector)
      .append("svg")
      .attr("width", width)
      .attr("height", height)
      .attr("class", "bubble");
  }

  wrap(text, width) {

        text.each(function() {
          var text = d3.select(this);
          var words = text.text().split(/\s+/).reverse(),
              word,
              line = [],
              lineNumber = 0,
              lineHeight = 1, // ems
              y = text.attr("y"),
              dy = parseFloat(text.attr("dy"));

          var tspan = text.text(null).append("tspan").attr("x", 0).attr("y", y).attr("dy", dy + "em");
					var tspanHeight = 20; //Math.abs(tspan[0][0]["y"]);
          while (word = words.pop()) {
            line.push(word);
            tspan.text(line.join(" "));
            if (tspan.node().getComputedTextLength() > this.currentBubbleWidth) {
              line.pop();
              tspan.text(line.join(" "));
              line = [word];
              var customY = y-tspanHeight;
              tspan.attr("y", customY);
              tspan = text.append("tspan").attr("x", 0).attr("y", customY ).attr("dy", ++lineNumber * lineHeight + dy + "em").text(word);
            }
          }
        });
  }

	draw(data){

    var layout = this.createLayout(data);
    var svg = this.createSvg(this.width, this.height);
    var nodes = this.generateNodes(svg, layout, data);
    var arc = this.generateBubbles(nodes);
    this.generateBubbleNames(nodes);
    this.generateOnHoverLabels(arc.arc, arc.arcEnter);
  }

  generateNodes(svg, layout, data){

  	var nodes = svg.selectAll("g.node").data(
      layout.nodes({ children: data }).filter(function(d) {
        return !d.children;
      })
    );
    nodes.enter().append("g").attr("class", "node").attr("transform", function(d) {
    	return "translate(" + d.x + "," + d.y + ")";
    });

    return nodes;
  }

  generateBubbles(nodes){

  	var pie = d3.layout.pie().sort(null);
    var arc = d3.svg.arc().innerRadius(this.radius).outerRadius(this.radius);

  	var arcGs = nodes.selectAll("g.arc").data(function(data) {
      return pie(data[1]).map(function(m) {
        m.r = data.r;
        m.label = data[0];

        return m;
      });
    });

    var color = d3.scale.ordinal().range(["#28a74580", "#dc3545a1", "#e8e8e8"]); //GREEN RED GRAY
    var arcEnter = arcGs.enter().append("g").attr("class", "arc");
    arcEnter
      .append("path")
      .attr("d", function(d) {
      arc.innerRadius(0); //d.r-10
      arc.outerRadius(d.r+10);
      return arc(d);
    })
      .style("fill", function(d, i) {
      return color(i);
    });

    return {arc: arc, arcEnter:arcEnter};
  }

  generateBubbleNames(nodes){

  	var labels = nodes.selectAll("text.label")
    .data(function(d) { return [d]; });

    labels.enter().append("text")
      .attr({
      "class": "label",
      dy: "0.35em"
    })
    .style("text-anchor", "middle")
    .text(function(d) {
      this.currentBubbleWidth = d.r / 5;
      var splittedWords = d[0].split(/\s+/).map(word => {
          var ending = word.length > this.currentBubbleWidth ? "…": "";
          return word.substring(0, this.currentBubbleWidth) + ending;
      });
      return splittedWords.join(" ");
    }).call(this.wrap, 100);
  }

  generateOnHoverLabels(arc, arcEnter){

  	arcEnter.append("text")
      .attr('x', function(d) { arc.outerRadius(d.r); return arc.centroid(d)[0]; })
      .attr('y', function(d) { arc.outerRadius(d.r); return arc.centroid(d)[1]; })
      .attr('dy', "0.35em")
      .style("text-anchor", "middle")
      .style("display", "none")
      .text(function(d) { return d.value; });
  }
}
