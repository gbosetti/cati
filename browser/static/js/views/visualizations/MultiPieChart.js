// gbosetti https://github.com/gbosetti
// http://jsfiddle.net/gal007/owtpzn03
class MultiPieChart{

  constructor(domSelector, width, height){

    this.domSelector = domSelector;
    this.width = width;
    this.height = height;
    this.radius = Math.min(width, height) / 2;
    this.zoomAndMoveEnabled = true;
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

  	var svg = d3.select($(this.domSelector)[0]) //So you we use more expressive power of JQUERY (e.g. the :visible selector)
      .append("svg")
      //.attr("style", "outline: thin dotted #e2e2e2;")
      .attr("width", width)
      .attr("height", height)
      .attr("class", "bubble")
      .call(d3.behavior.zoom().on("zoom", (evt) => {
      	svg.attr("transform", "translate(" + d3.event.translate + ")" + " scale(" + d3.event.scale + ")");
      }))
      .append("g"); //.attr("id", "draggable-area");

      return svg;
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
					var tspanHeight = 1.5*parseInt(tspan.style("font-size")).toFixed(0);

while (word = words.pop()) {
            line.push(word);
            tspan.text(line.join(" "));
            //if (tspan.node().getComputedTextLength() > this.currentBubbleWidth) {
              line.pop();
              tspan.text(line.join(" "));
              line = [word];
              var customY = y-tspanHeight;
              tspan.attr("y", customY);
              tspan = text.append("tspan").attr("x", 0).attr("y", customY ).attr("dy", ++lineNumber * lineHeight + dy + "em").text(word);
            //}
          }
        });
  }

	draw(data){
	    $(this.domSelector).html="";
        var layout = this.createLayout(data);
        var svg = this.createSvg(this.width, this.height);
        var nodes = this.generateNodes(svg, layout, data);
        this.tooltip = this.createTooltip();
        this.generateBubbles(nodes, this.tooltip);
        this.generateBubbleNames(nodes);
  }

  generateNodes(svg, layout, data){

  	var nodes = svg.selectAll("g.node").data(
      layout.nodes({ children: data }).filter(function(d) {
        return !d.children;
      })
    );
    nodes.enter().append("g").attr("class", "node").attr("transform", function(d) {

        var x_axis = isNaN(d.x)? 0 : d.x;
        var y_axis = isNaN(d.y)? 0 : d.y;
        //console.log("INFO:", x_axis + "," + y_axis);

    	return "translate(" + x_axis + "," + y_axis + ")";
    });

    return nodes;
  }

  generateBubbles(nodes, tooltip){

  	var pie = d3.layout.pie().sort(null);
    var arc = d3.svg.arc().innerRadius(this.radius).outerRadius(this.radius);

    //Creating each pie
  	var arcGs = nodes.selectAll("g.arc").data(function(data) {
      return pie(data[1]).map(function(m) {
        m.totalCount = data.value;
        m.r = data.r;
        m.label = data[0];

        return m;
      });
    });

    var color = d3.scale.ordinal().range(["#28a74580", "#dc3545a1", "#e8e8e8"]); //GREEN RED GRAY
    var arcEnter = arcGs.enter().append("g").attr("class", "arc");
    var self = this;

    //Creating each section in the pie
     arcEnter
        .append("path")
        .attr("d", function(d) {
          arc.innerRadius(0); //d.r-10
          arc.outerRadius(d.r+10);
          return arc(d);
        })
        .style("fill", function(d, i) {
          return color(i);
        })
        .on("mouseover", function(evt, idx){self.mouseOver(evt, this)})
        .on("mousemove", function(evt, idx){self.mouseMove(evt, this)})
        .on("mouseout", function(evt, idx){ self.mouseOut(evt, this); })
        .on("click", (evt) => { this.onBubbleClick(evt.label, evt) }); //this.onBubbleClick);

    return {arc: arc, arcEnter:arcEnter};
  }

  mouseMove(data, ele){
    d3.event.preventDefault(); d3.event.stopPropagation();
    //this.zoomAndMoveEnabled = false;
    return this.tooltip.style("top", (d3.event.pageY-10)+"px")
    	.style("left",(d3.event.pageX+10)+"px");
  }

  mouseOut(data, elem) {
    d3.event.preventDefault(); d3.event.stopPropagation();
    //this.zoomAndMoveEnabled = true;
    d3.select(elem).style("transform", "scale(1,1)");
    return this.tooltip.style("visibility", "hidden");
  }

  mouseOver(data, elem){

    d3.event.preventDefault(); d3.event.stopPropagation();
    //this.zoomAndMoveEnabled = false;
    this.tooltip.html(
    	data.label +
      "<br>" + (data.data * 100 / data.totalCount).toFixed(1) + "% " +
      "(" + data.data + " of " + data.totalCount + ")"
      );
    this.tooltip.style("visibility", "visible");
    d3.select(elem).style("transform", "scale(1.07,1.07)");
  }

  createTooltip(){
        return d3.select("body")
          .append("div")
          .style("position", "absolute")
          .style("display", "block")
          .style("z-index", "10")
          .style("visibility", "hidden")
          .style("color", "white")
          .style("padding", "8px")
          .style("background-color", "rgba(0, 0, 0, 0.75)")
          .style("border-radius", "6px")
          .style("font", "12px sans-serif")
          .text("tooltip");
    }

  generateBubbleNames(nodes){
		// Math.min(2 * d.r, (2 * d.r - 8) / this.getComputedTextLength() * 24)
    var maxCharacters = 10;
  	var labels = nodes.selectAll("text.label")
    .data(function(d) { return [d]; });

    labels.enter()
    .append("text")
    //.on("click", (evt) => { this.onBubbleClick(evt[0], evt) })
    .attr({
      "class": "label",
      dy: "0.35em"
    })
    .style("text-anchor", "middle")
    .style("font-size", function(d) { return d.r / 3; })
    .text(function(d) {
      var splittedWords = d[0].split(/\s+/).map(word => {
          var ending = word.length > maxCharacters ? "…": "";
          return word.substring(0, maxCharacters) + ending;
      });
      return splittedWords.join(" ");
    })
    .on("mousedown", function(){
        d3.event.stopPropagation();
    })
    .call(this.wrap, 200);


  };

  onBubbleClick(data, evt){
    console.log("Default behaviour", data);
  }
}


