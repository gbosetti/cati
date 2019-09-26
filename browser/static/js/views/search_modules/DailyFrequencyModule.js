class DailyFrequencyModule extends SearchModule{

    constructor(containerSelector, client) {

        super(containerSelector);
        this.client = client;
    }

    loadTweets(data){
        this.requestTweetsFrequency(data).then(response => {
            this.presentTweetsFrequency(response, '#tweets_timeline_results');
        });
    }

    requestTweetsFrequency(data) {

        return new Promise((resolve, reject)=>{
            $.post(app.appURL+'get_tweets_frequency', data, function(response){

                 resolve(response);

            }, 'json').fail(function(err) { console.log("Error:", err); });
        });
    }

    loadSlider(domSelector){

        this.slider = $(domSelector)[0];
        noUiSlider.create(this.slider, {
            start: [0, 1],
            connect: true,
            direction: 'ltr',  // ltr or rtl
            orientation: 'horizontal',
            tooltips: false,
            range: { 'min': 0, 'max': 1 }
        });
        this.slider.noUiSlider.on('set', values => {
            if(this.slider_data)
                this.sliderUpdate(values, this.slider_data);
        });
    }

    presentTweetsFrequency(data, chartSelector){

        var max_date = new Date(data[0][0]).toLocaleDateString();
        var min_date = new Date(data[data.length-1][0]).toLocaleDateString();

        $(chartSelector).html(`<svg id="tweets_timeline_results_svg"></svg>
                                <div class="freq-slider-area">
                                    <div id="freq-slider-range-vertical" class="slider-range"></div>
                                    <div class="row pt-3 ">
                                        <div class="col-md-6 text-left">
                                            <b>From:</b> <span>${min_date}</span>
                                        </div>
                                        <div class="col-md-6 text-right">
                                            <b>To:</b> <span>${max_date}</span>
                                        </div>
                                    </div>
                                </div>

                                <div class="row pt-3">
                                    <div class="col-12 pix-margin-top-20 pix-margin-bottom-20 state_btns" style="text-align: right;">
                                        Mark the tweets matching the selection as:
                                        <a href="#" data-cid="" data-state="negative" class="timeline_btn options_btn_negative geo_selection_to_state">Negative</a>
                                        <a href="#" data-state="confirmed" class="timeline_btn options_btn_valid geo_selection_to_state">Confirmed</a>
                                        <a href="#" data-state="unlabeled" class="timeline_btn options_btn_clear geo_selection_to_state">Unlabeled</a>
                                    </div>
                                </div>`);
         this.loadSlider("#freq-slider-range-vertical");

        //        Demo data
        //        var barchartdata = [{
        //            "key": "Tweets frequency",
        //            "values": [
        //                [1209528000000, 3.86],
        //                [1293771600000, 1.34],
        //                [1296450000000, 0]
        //            ]
        //        }];

        var barchartdata = [{
            "key": "Tweets frequency",
            "values": data
        }];

        var chart;
        nv.addGraph(function() {
          chart = nv.models.stackedAreaChart()
            .useInteractiveGuideline(true)
            .showControls(false)
            .showLegend(false)
            .x(function(d) {
              return d[0]
            })
            .y(function(d) {
              return d[1]
            })
            .duration(300)
            .clipEdge(false);

          chart.xAxis.tickFormat(function(d) {
            return d3.time.format('%d/%m/%Y')(new Date(d))
          });

          d3.select("#tweets_timeline_results_svg")
            .datum(barchartdata)
            .transition().duration(1000)
            .call(chart)

          nv.utils.windowResize(chart.update);

          $("#tweets_timeline_results_svg g")[0].setAttribute("transform", "translate(30,30)")

          return chart;
        });
    }
}