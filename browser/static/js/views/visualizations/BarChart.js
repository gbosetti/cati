// https://github.com/gbosetti
class BarChart{

	constructor(containerSelector, width, height, labels, colors){

    this.containerSelector = containerSelector;
  	this.margin = {top: 20, right: 160, bottom: 75, left: 30};
    this.height = height - this.margin.top - this.margin.bottom;
    this.width = width - this.margin.left - this.margin.right;
		this.labels = labels;
    this.colors = colors || ["#28a745", "#dc3545", "#e8e8e8"];
	}

  transformData(labels, data){

  	// Data to layers/matrix
    return d3.layout.stack()(labels.map(function(fruit) {
      return data.map(function(d) {
        return {x: d.label, y: +d[fruit]};
      });
    }));
  }

  fillChartWithData(dataset){

    // Set x, y and colors
    var x = d3.scale.ordinal()
      .domain(dataset[0].map(function(d) { return d.x; }))
      .rangeRoundBands([10, this.width-10], 0.02);

    var y = d3.scale.linear()
      .domain([0, d3.max(dataset, function(d) {  return d3.max(d, function(d) { return d.y0 + d.y; });  })])
      .range([this.height, 0]);

      return {x:x, y:y}
  }

  createDrawingArea(selector){

  	return d3.select(selector)
      .append("svg")
      .attr("width", this.width + this.margin.left + this.margin.right)
      .attr("height", this.height + this.margin.top + this.margin.bottom)
      .append("g")
      .attr("transform", "translate(" + this.margin.left + "," + this.margin.top + ")");
  }

  renderAxis(svg, coord){

  	// AXIS
    var yAxis = d3.svg.axis()
      .scale(coord.y)
      .orient("left")
      .ticks(5)
      .tickSize(-this.width, 0, 0)
      .tickFormat( function(d) { return d } );
    svg.append("g")
      .attr("class", "y axis")
      .call(yAxis);

    var xAxis = d3.svg.axis()
      .scale(coord.x)
      .orient("bottom");
    svg.append("g")
      .attr("class", "x axis").attr("transform", "translate(0," + this.height + ")")
      .call(xAxis).selectAll("text")
        .attr("y", 30)
        .attr("x", 10)
        .attr("dy", "-0.35em")
        .attr("transform", "rotate(45)")
        .style("text-anchor", "start");

  }

  loadSeries(svg, dataset, coord, tooltip){

  // Prep the tooltip bits, initial display is hidden
    var tooltip = svg.append("g")
      .attr("class", "tooltip")
      .style("display", "none");

    tooltip.append("rect")
      .attr("width", 30)
      .attr("height", 20)
      .attr("fill", "white")
      .style("opacity", 0.5);

    tooltip.append("text")
      .attr("x", 15)
      .attr("dy", "1.2em")
      .style("text-anchor", "middle")
      .attr("font-size", "12px")
      .attr("font-weight", "bold");

  	// Create groups for each series, rects for each segment
    var groups = svg.selectAll("g.cost")
      .data(dataset)
      .enter().append("g")
      .attr("class", "cost")
      .style("fill", (d, i) => { return this.colors[i]; });

    var rect = groups.selectAll("rect")
      .data(function(d) { return d; })
      .enter()
      .append("rect")
      .attr("x", function(d) { return coord.x(d.x); })
      .attr("y", function(d) { return coord.y(d.y0 + d.y); })
      .attr("height", function(d) { return coord.y(d.y0) - coord.y(d.y0 + d.y); })
      .attr("width", coord.x.rangeBand())
      .on("mouseover", function() { tooltip.style("display", null); })
      .on("mouseout", function() { tooltip.style("display", "none"); })
      .on("mousemove", function(d) {
        var xPosition = d3.mouse(this)[0] - 15;
        var yPosition = d3.mouse(this)[1] - 25;
        tooltip.attr("transform", "translate(" + xPosition + "," + yPosition + ")");
        tooltip.select("text").text(d.y);
      });
  }

  drawLegends(svg){

  	// Draw legend
    var legend = svg.selectAll(".legend")
      .data(this.colors)
      .enter().append("g")
      .attr("class", "legend")
      .attr("transform", function(d, i) { return "translate(30," + i * 19 + ")"; });

    legend.append("rect")
      .attr("x", this.width - 18)
      .attr("width", 18)
      .attr("height", 18)
      .style("fill", (d, i) => {return this.colors.slice().reverse()[i];});

    legend.append("text")
      .attr("x", this.width + 5)
      .attr("y", 9)
      .attr("dy", ".35em")
      .style("text-anchor", "start")
      .text(function(d, i) {
        switch (i) {
          case 0: return "Unlabeled";
          case 1: return "Negative";
          case 2: return "Confirmed";
        }
      });
  }

	draw(data){

    var svg = this.createDrawingArea(this.containerSelector);
    var dataset = this.transformData(this.labels, data);
    var coord = this.fillChartWithData(dataset);
    this.renderAxis(svg, coord);
		this.loadSeries(svg, dataset, coord);
		this.drawLegends(svg);
  }
}

