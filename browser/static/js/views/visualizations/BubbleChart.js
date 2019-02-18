class BubbleChart{

    constructor(graphAreaSelector, width, height, colorRange){

        this.height = height;
        this.colorRange = colorRange || ["#ffe5cb", "#ff7f0e"];
        this.graphAreaSelector = graphAreaSelector;
        this.width = width || $(graphAreaSelector).width();
    }

    onBubbleClick(e){
        console.log("Default behaviour");
    }

    // Returns a flattened hierarchy containing all leaf nodes under the root.
    classes(root) {
        var classes = [];

        function recurse(name, node) {
          if (node.children) node.children.forEach(function(child) { recurse(node.name, child); });
          else classes.push({packageName: name, className: node.name, value: node.size});
        }

        recurse(null, root);
        return {children: classes};
    }

    draw(data){

        var layout = d3.layout.pack()
          .sort(null)
          .size([this.width, this.height])
          .padding(10);

        var svg = d3.select(this.graphAreaSelector).append("svg")
          .attr("width", this.width)
          .attr("height", this.height)
          .attr("class", "bubble");

        var tooltips = this.createTooltip();

        d3.select(self.frameElement).style("height", this.height + "px");

        this.createNodes(svg, layout, data, tooltips);
    }

    createTooltip(){
        return d3.select("body")
          .append("div")
          .style("position", "absolute")
          .style("z-index", "10")
          .style("visibility", "hidden")
          .style("color", "white")
          .style("padding", "8px")
          .style("background-color", "rgba(0, 0, 0, 0.75)")
          .style("border-radius", "6px")
          .style("font", "12px sans-serif")
          .text("tooltip");
    }

    createNodes(svg, layout, root, tooltip){

        var ocurrences = root.children.map(row => { return row.size });
        var format = d3.format(",d"), color = d3.scale.linear().domain([ Math.min(...ocurrences), Math.max(...ocurrences)]).range(this.colorRange); // d3.scale.category20c();

        var node = svg.selectAll(".node")
            .data(layout.nodes(this.classes(root))
            .filter(function(d) { return !d.children; }))
            .enter().append("g")
            .attr("class", "node")
            .attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });

        node.append("circle")
            .attr("r", function(d) { return d.r; })
            .style("fill", function(d, i) {
                return color(d.value);
            })
            .on("mouseover", function(d) {
                tooltip.text(d.className + ": " + format(d.value));
                tooltip.style("visibility", "visible");
                var circle = d3.select(this);
                circle.style("transform", "scale(1.3,1.3)");
                //circle.style("transform", "scale(1.1,1.1)");
                //circle.style("font-size", "20px");
                //circle[0][0].style["font"] = "20px sans-serif";
            })
            .on("mousemove", function() {
                return tooltip.style("top", (d3.event.pageY-10)+"px").style("left",(d3.event.pageX+10)+"px");
            })
            .on("mouseout", function(){
                d3.select(this).style("transform", "scale(1,1)");
                return tooltip.style("visibility", "hidden");
            })
            .on("click", (ev) => {
                this.onBubbleClick(ev);
            });

        node.append("text")
            .attr("dy", ".3em")
            .style("text-anchor", "middle")
            .style("pointer-events", "none")
            .text(function(d) { return d.className.substring(0, d.r / 5); });

        return node;
    }
}