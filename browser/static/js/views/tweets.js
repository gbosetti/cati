app.views.tweets = Backbone.View.extend({
    template: _.template($("#tpl-page-tweets").html()),
    events: {
        'submit #tweets_form': 'tweets_submit',
        'click .retweet_state': 'retweet_state',
        'click .cluster_tweets': 'cluster_tweets',
        'click .scroll_tweets': 'scroll_tweets',
        'click .cluster_state': 'cluster_state',
        'click .btn_filter': 'filter_tweets',
        'click .massive_tagging_to_state': 'massive_tagging_to_state',
        'click #search_not_labeled': 'search_not_labeled'
    },
    initialize: function() {

        this.bigrams = { //Session data for the bigrams
            bigrams: undefined,
            tweets: undefined,
            graphHeight: undefined,
            formData: []
        };

        //this.render();
        //this.updatingSearchDatesRange();
        //var handler = _.bind(this.render, this);
        $(document).on("click","body .tweet_state",(e) => {
			this.tweet_state(e);
		});
		$(document).on("click",".search-accordion .card-header",function(e){
			if(e.target.tagName.toLocaleLowerCase() == "div")
			    e.target.querySelector("a").click();
		});
    },
    /*updatingSearchDatesRange: function(){

        var data = this.getIndexAndSession();
        $.post(app.appURL+'get_dataset_date_range', data, function(response){
            $("#search-start-date")[0].valueAsDate = new Date(response.min_timestamp.value);
            $("#search-end-date")[0].valueAsDate = new Date(response.max_timestamp.value);
        }, 'json').fail(self.cnxError);
    },*/
    render: async function(){
        var html = this.template();
        this.$el.html(html);
        this.delegateEvents();
        await app.views.mabed.prototype.setSessionTopBar();
        app.views.mabed.prototype.getClassificationStats();
        $('.popover-dismiss').popover({
          trigger: 'focus',
          html: true,
          content:  'The search query supports the following special characters:<ul>'+
                    '<li> + signifies AND operation</li>'+
                    '<li> | signifies OR operation</li>'+
                    '<li> - negates a single token</li>'+
                    '<li> " wraps a number of tokens to signify a phrase for searching</li>'+
                    '<li> * at the end of a term signifies a prefix query</li>'+
                    '<li> ( and ) signify precedence</li>'+
                    '<li> ~N after a word signifies edit distance (fuzziness)</li>'+
                    '<li> ~N after a phrase signifies slop amount</li></ul>'
        });

        $("[name=word]").focus();

        return this;
    },
    tweets_submit: function(e){
      e.preventDefault();
      if(!app.session){
          $.confirm({
                title: 'Error',
                boxWidth: '800px',
                theme: 'pix-danger-modal',
                backgroundDismiss: true,
                content: "Error! please select a session from the settings page.",
                buttons: {
                    cancel: {
                        text: 'CLOSE',
                        btnClass: 'btn-primary',
                    }
                }
            });
          return false;
      }

      $('.tweets_results').fadeOut('slow');
      $('.loading_text:visible:last').fadeIn('slow');

      if(document.querySelector("#search-results-tabs-area").hidden == true)
        this.bigrams.formData = this.getBigramsFormData();

      this.clearAllResultsTabs();
      this.searchForTweets(); //Submit
      return false;
    },
    loadGeopositionedTweets: function(data){
        console.log("loadGeopositionedTweets");
        try{
            new GeoSpatialModule("#mapid", this).loadTweets(data);
        }catch(err){console.log(err)}
    },
    searchForTweets: function(){

        this.clearAllResultsTabs();
        this.showResultsArea();
        $('.loading_text:visible:last').fadeIn('slow');
        var tabData = this.getCurrentSearchTabData("#search-results-tabs li.active a");
        this.renderAccordionInTab(tabData.target, tabData.label);
        var retweetsContainer=".top_retweets_results";

        var data = this.getIndexAndSession().concat(this.getTabSearchData()).concat(this.bigrams.formData)
            .concat([{name: "retweets_number", value: 20}, {name: "image_clusters_limit", value:20}]);
        var startingReqTime = performance.now();

        var query = data.filter(item => {return item.name == "word"})[0].value;

        if(query && query.trim() != ""){ //If the user has entered at least a keyword

            this.requestTweets(data, startingReqTime);
            this.loadTweetsTimeline(data);
            this.loadGeopositionedTweets(data);
            this.loadRetweets(data, retweetsContainer);
            this.requestNgrams(data);

        } else { //If the user has entered no keyword

            this.hideNotFullSearchSearch();
            this.loadGeopositionedTweets(data);
            this.loadRetweets(data, retweetsContainer);
            this.requestNgrams(data).then(
                (res) => { //In case of success
                    this.showResultsWarning();
                    this.showResultsStats(res["total_matching_tweets"], startingReqTime, "all the tweets in the dataset");
                },
                (err) => { //In case of failing
                    this.showNoBigramsFound(".ngrams-search-classif:visible:last");
            });
            this.requestFullImageClusters(data).then(
                res => {
                    this.showImageClusters(res.clusters, undefined, '.imagesClusters:visible:last', undefined, undefined, res.total_clusters);
                },
                err => { //In case of failing
                    this.clearContainer(".imagesClusters");
                    this.showNoTweetsFound(".imagesClusters");
            });
        }
        app.views.mabed.prototype.getClassificationStats();
    },
    loadTweetsTimeline: function (data) {

        this.requestTweetsFrequency(data).then(response => {
            this.presentTweetsFrequency(response, '#tweets_timeline_results_svg');
        });
    },
    requestTweetsFrequency: function (data) {

        return new Promise((resolve, reject)=>{

            console.log("\nfreq");

            $.post(app.appURL+'get_tweets_frequency', data, function(response){

                 console.log("RESPONSE FROM get_tweets_frequency", response);

            }, 'json').fail(function(err) {
                    console.log("Error:", err);
            });
        });
    },
    presentTweetsFrequency(data, chartSelector){

        $(chartSelector).html("");

//        Demo data
//        var barchartdata = [{
//            "key": "Tweets frequency",
//            "values": [
//                [1209528000000, 3.8699674365231],
//                [1214798400000, 6.7571718894253],
//                [1293771600000, 1.340824670897],
//                [1296450000000, 0]
//            ]
//        }];

        console.log("loadTweetsTimeline", data);
        var barchartdata = []

        var chart;
        nv.addGraph(function() {
          chart = nv.models.stackedAreaChart()
            .useInteractiveGuideline(true)
            .x(function(d) {
              return d[0]
            })
            .y(function(d) {
              return d[1]
            })
            .duration(300);

          chart.xAxis.tickFormat(function(d) {
            return d3.time.format('%x')(new Date(d))
          });

          d3.select(chartSelector)
            .datum(barchartdata)
            .transition().duration(1000)
            .call(chart)

          return chart;
        });
    },
    loadRetweets(data, retweetsContainer){
        console.log("loadRetweets");
        new TopRetweetsModule(retweetsContainer, this).loadTweets(data);
    },
    hideNotFullSearchSearch: function(){

        $(".card").each((key, cardElem) => {
            if( !cardElem.querySelector(".collapse").classList.contains("collapseNgrams") &&
                !cardElem.querySelector(".collapse").classList.contains("collapseRetweets") &&
                !cardElem.querySelector(".collapse").classList.contains("collapseImages")&&
                !cardElem.querySelector(".collapse").classList.contains("collapseGeopositioned"))
                cardElem.hidden = true;
        });
    },
    showResultsWarning: function(){

        $(".full-search-warning:last")[0].hidden = false;
    },
    clearAllResultsTabs: function(){
        /*document.querySelectorAll("#search-results-tabs li a").forEach(elem => {
            $(elem.target).html("");
        });*/
        $(".search-results-tabs-content").html(`
            <div class="tab-content container clearfix">
                <!-- ALL RESULTS -->
                <div class="tab-pane active" id="all-search-results"></div>

                <!-- UNLABELED RESULTS -->
                <div class="tab-pane active" id="unlabeled-results"></div>

                <!-- POSITIVE RESULTS -->
                <div class="tab-pane active" id="confirmed-results"></div>

                <!-- NEGATIVE RESULTS -->
                <div class="tab-pane active" id="rejected-results"></div>
            </div>`);
    },
    renderAccordionInTab: function(tab, label){

        $(tab).html(`<div class="full-search-warning mt-4 alert alert-warning" hidden>
                        <strong>You have not specified keywords for the search.</strong> You can explore the full dataset and try searching for some combination of the words below:
                            <span class="close">
                            <span aria-hidden="true"><i class="fa fa-info-circle"></i></span>
                        </button>
                    </div>
                    <div class="mt-3 col-12 loading_text">
                        <span class="badge badge-secondary">Loading...</span>
                    </div>

                    <div class="mt-4 col-12 tweets_results"><span class="res_num">0</span> results (<span class="res_time">0.1</span> seconds) matching <span class="res_keywords">"«»"</span></div>

                    <div class="col-12 pix-margin-top-20 pix-margin-bottom-20 state_btns" style="">
                        Mark all the results as:
                        <a href="#" data-cid="" data-state="negative" class="timeline_btn options_btn_negative massive_tagging_to_state">Negative</a>
                        <a href="#" data-state="confirmed" class="timeline_btn options_btn_valid massive_tagging_to_state">Confirmed</a>
                        <a href="#" data-state="proposed" class="timeline_btn options_btn_clear massive_tagging_to_state">Unlabeled</a>
                    </div>

                    <div class="container">
                      <div class="full-search-ngrams-classif" hidden></div>
                      <div class="search-accordion">

                                <div class="card">
                                  <div class="card-header"><a class="card-link" data-toggle="collapse" href="#collapseGeopositioned">Tweets timeline</a></div>
                                  <div id="collapseGeopositioned" class="collapse show collapseGeopositioned">
                                    <div class="card-body">

                                        <!-- TWEETS TIMELINE SECTION -->
                                        <div class="col-12 tweets_timeline_results">
                                            <svg id="tweets_timeline_results_svg"></svg>
                                        </div>

                                    </div>
                                  </div>
                                </div>

                                <div class="card">
                                  <div class="card-header"><a class="card-link" data-toggle="collapse" href="#collapseGeopositioned">Geopositioned tweets</a></div>
                                  <div id="collapseGeopositioned" class="collapse show collapseGeopositioned">
                                    <div class="card-body">

                                        <!-- GEOPOSITIONED TWEETS SECTION -->
                                        <div class="col-12 geopositioned_tweets_results">
                                            <div class="pl-0 mt-1 mb-2 col-12 tweets_results_label geo_tweets_results" style="display: block;"></div>
                                            <div id="mapid" style="height: 500px; width: 100%; margin-left:auto; margin-right:auto;"></div>

                                            <div class="maps-slider-area">
                                                <div id="maps-slider-range-vertical" class="slider-range"></div>

                                                <div class="row pt-3 ">
                                                    <div class="col-md-6 text-left">
                                                        <b>From:</b> <span id="maps-date-lower"></span>
                                                    </div>
                                                    <div class="col-md-6 text-right">
                                                        <b>To:</b> <span id="maps-date-upper"></span>
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
                                            </div>
                                        </div>

                                    </div>
                                  </div>
                                </div>

                                <div class="card">
                                  <div class="card-header"><a class="card-link" data-toggle="collapse" href="#collapseNgrams">Results grouped by ngrams</a></div>
                                  <div id="collapseNgrams" class="collapse show collapseNgrams"> <!-- class="collapse show" -->
                                    <div class="card-body">

                                       <!-- NGRAMS CLUSTERS RESULTS -->
                                      <div class="col-12 pix-margin-top-10">
                                        <div class="ngrams-search-classif"></div>
                                      </div>

                                    </div>
                                  </div>
                                </div>

                                <div class="card">
                                  <div class="card-header"><a class="card-link collapse-images-title" data-toggle="collapse" href="#collapseImages">Top image-based clusters</a></div>
                                  <div id="collapseImages" class="collapse show collapseImages">
                                    <div class="card-body image-clusters-container">

                                        <div class="collapse-images-matching tweets_results_label pl-0 mt-1 mb-2 col-12"></div>

                                        <!-- IMAGE CLUSTERS RESULTS -->
                                        <div class="col-12 pix-margin-top-10 images-clusters-container">
                                            <div class="card-columns imagesClusters"></div>
                                        </div>

                                    </div>
                                  </div>
                                </div>

                                <div class="card">
                                  <div class="card-header"><a class="card-link top-retweets-header" data-toggle="collapse" href="#collapseRetweets">Top retweets</a></div>
                                  <div id="collapseRetweets" class="collapse show collapseRetweets">
                                    <div class="card-body">

                                        <!-- POPULAR RETWEETS RESULTS -->
                                        <div class="col-12 top_retweets_results"></div>

                                    </div>
                                  </div>
                                </div>

                                <div class="card">
                                  <div class="card-header"><a class="card-link" data-toggle="collapse" href="#collapseIndividual">Individual results</a></div>
                                  <div id="collapseIndividual" class="collapse show collapseIndividual">
                                    <div class="card-body">

                                        <!-- INDIVIDUAL TWEET RESULTS -->
                                        <div class="col-12 individual_tweets_result"></div>

                                    </div>
                                  </div>
                                </div>
                      </div>
                    </div>`);
    },
    showResultsArea: function(){

        if(document.querySelector("#search-results-tabs-area").hidden == false) // IF IT IS THE FIRST SEARCH
            return;

        document.querySelector("#search-results-tabs-area").hidden = false;

        var self = this;
        $('#search-results-tabs-area .nav-item a').on( 'click', function () {
            $( '#search-results-tabs-area' ).find( 'li.active' ).removeClass( 'active' );
            $( this ).parent( 'li' ).addClass( 'active' );

            //If the tab is empty, run a query
            var html = $(this.target).html();
            if( html && html.trim().length > 0 ){
                console.log("CONTAINING SOMETHING")
            }
            else { console.log("EMPTY"); self.searchForTweets(); }
        });
    },
    getCurrentSearchTabData: function(selector){
        var tab = document.querySelector(selector);
        return {
            label: tab.getAttribute("tag"),
            target: document.querySelector(tab.target)
        };
    },
    requestTweets: function(data, startingReqTime){

        //First clean the previous results
        var imageClustersSelector = '.imagesClusters';
        $(imageClustersSelector).html("");

        new SearchModule(".image-clusters-container","spinner-images").enableLoading();
        new SearchModule(".individual_tweets_result","spinner-individual").enableLoading();

        var individualTweetsSelector = '.individual_tweets_result';
        $(individualTweetsSelector).html("");
        this.showLoadingMessage(individualTweetsSelector, 400);

        var self = this;
        $.post(app.appURL+'search_for_tweets', data, function(response){
            self.displayPaginatedResults(response, startingReqTime, data[0].value, data.find(row => row.name == "search_by_label").value);

            new SearchModule(".image-clusters-container","spinner-images").disableLoading();
            new SearchModule(".individual_tweets_result", "spinner-individual").disableLoading();

        }, 'json').fail(this.cnxError);
    },
    requestFullImageClusters: function(data){
        return new Promise((resolve, reject) => {
            $.post(app.appURL+'search_for_image_clusters', data, (response) => {
                resolve(response);
            }, 'json').fail((err)=>{
                this.cnxError(err);
                reject(err)
            });
        });
    },
    requestNgrams: function(data){

        var self = this;
        console.log("requestNgrams");
        return new Promise((resolve, reject) => {

            this.bigrams.lastQueryParams = data;
            this.updateBigramsFormData(data);

            var containerSelector = ".ngrams-search-classif";
            //self.showLoadingMessage(containerSelector, 677); ...
            new SearchModule(containerSelector,"spinner-ngrams").enableLoading();

            $.post(app.appURL+'ngrams_with_higher_ocurrence', data, (response) => {
                //check if there are any ngrams
                if($.isEmptyObject(response.ngrams)){
                    self.showNoBigramsFound(containerSelector);
                }else {
                    self.showNgramsClassification(response.classiffication, response.ngrams, containerSelector, 500, self.bigrams);
                }
                new SearchModule(containerSelector,"spinner-ngrams").disableLoading();
                resolve(response)

            }, 'json').fail(function(err){
                new SearchModule(containerSelector,"spinner-ngrams").disableLoading();
                self.clearNgramsGraph();
                self.cnxError(err);
                reject(err)
            });
        });
    },
    clearContainer: function(selector){
        $(selector).html("");
    },
    clearNgramsGraph: function(){
        this.clearContainer(".bigrams-graph-area:visible");
    },
    showNoTweetsFound: function(containerSelector){
        $(containerSelector).html("Sorry, no re-tweets were found under this criteria.");
    },
    showNoBigramsFound: function(containerSelector){
        $(containerSelector).html("Sorry, no bigrams were found under this criteria.");
    },
    showNoTweetsFound: function(containerSelector){
        $(containerSelector).html("Sorry, no tweets were found under this criteria.");
    },
    showNoImageClustersFound: function(containerSelector){
        $(containerSelector).html("Sorry, no image clusters were found under this criteria.");
    },
    showLoadingMessage: function(containerSelector, height){

        new SearchModule(containerSelector).enableLoading();
    },
    cnxError: function(err) {
        $('.loading_text:visible:last').fadeOut('slow');
        var err_content = "An error was encountered while connecting to the server, please try again." + ((err && err.statusText)? " Error's status: " + err.statusText : " ");
        $.confirm({
            title: 'Error',
            boxWidth: '600px',
            theme: 'pix-danger-modal',
            backgroundDismiss: true,
            content: err_content,
            buttons: {
                cancel: {
                    text: 'CLOSE',
                    btnClass: 'btn-cancel',
                }
            }
        });
    },
    get_retweets_html: function(aggregations, classes){

        var html = "";
        var template = _.template($("#tpl-item-retweet").html());

        $.each(aggregations, function(i, aggregation){
            var imgs = "";
            var retweet = aggregation.top_text_hits.hits.hits[0];

            if('extended_entities' in retweet._source){
              $.each(retweet._source.extended_entities.media, function(i, media){
                    var ext = "jpg";
                    if(media.media_url.endsWith("png")){
                        ext = "png";
                    }
                        imgs += '<a href="'+app.imagesURL+app.imagesPath+'/'+retweet._source.id_str+"_"+i+'.'+ext+'" target="_blank"><img style="margin:2px;max-height:150px;width:auto;" src="'+app.imagesURL+app.imagesPath+'/'+retweet._source.id_str+"_"+i+'.'+ext+'"></a>'
              });
            }
            //var state = retweet._source['session_'+app.session.s_name];
			matchingTweets = '<h6><span class="badge badge-secondary"> Matching tweets: '+aggregation.doc_count+'</span></h6>';

		    try{
            html += template({
                tid: retweet._id,
                          link: retweet._source.link,
                          text:  retweet._source.text,
                          images: imgs,
                          classes: "",
                          matching_tweets: matchingTweets
                        });
            }catch(err){console.log(err)}
        });
        return html;
    },
    get_tweets_html: function(response, classes, loadMoreButtonClass){

        loadMoreButtonClass = (loadMoreButtonClass && loadMoreButtonClass.length && loadMoreButtonClass.trim().length > 0)? loadMoreButtonClass : "";
        var html = "";
        var template = _.template($("#tpl-item-tweet").html());

        $.each(response.tweets.results, function(i, tweet){
            var imgs = "";
            var t_classes = classes;
            if(response.search_tweets){
                var detected = false;
                $.each(response.search_tweets, function(i2, t){
                    if(t._source.id_str===tweet._source.id_str){
                        detected=true;
                        return false;
                    }
                });
                if(!detected){
                    t_classes+= ' yellow-tweet';
                }
            }
            if('extended_entities' in tweet._source){
              $.each(tweet._source.extended_entities.media, function(i, media){
                    var ext = "jpg";
                    if(media.media_url.endsWith("png")){
                        ext = "png";
                    }
                        imgs += '<a href="'+app.imagesURL+app.imagesPath+'/'+tweet._source.id_str+"_"+i+'.'+ext+'" target="_blank"><img style="margin:2px;max-height:150px;width:auto;" src="'+app.imagesURL+app.imagesPath+'/'+tweet._source.id_str+"_"+i+'.'+ext+'"></a>'
              });
            }
            var state = tweet._source['session_'+app.session.s_name];
				if(state === "confirmed"){
					state = '<span class="badge badge-success">'+state+'</span>';
				}else if (state === "negative"){
					state = '<span class="badge badge-danger">'+state+'</span>';
				}else{
					state = '<span class="badge badge-secondary">'+state+'</span>';
				}
            html += template({
                tid: tweet._id,
                          name: tweet._source.user? "@" + tweet._source.user.name : undefined,
                          screen_name: tweet._source.user? tweet._source.user.screen_name : undefined,
                          created_at: tweet._source.created_at,
                          link: tweet._source.link,
                          text:  tweet._source.text,
                          classes: t_classes,
                          images: imgs,
                            state: state
                        });
        });
        if(response.tweets.scroll_size>0){
            html += '<div class="pix-margin-top-10"><a href="#" class="btn btn-lg btn-outline-success full_width ' + loadMoreButtonClass + '" data-scroll="'+response.tweets.scroll_size+'" data-sid="'+response.tweets.sid+'"> <strong>Load more tweets</strong> </a></div>';
        }
        return html;
    },
    showNgramTweets: function(clientData, client, ngramsToGenerate, ngramLabel, ngram, searchClass, endpoint){

        var self = this;
        $.confirm({
            theme: 'pix-cluster-modal',
            title: "Tweets matching the " + ngramsToGenerate + "-gram «" + ngramLabel + "»",
            columnClass: 'col-md-12',
            useBootstrap: true,
            backgroundDismiss: false,
            content: 'Loading... <div class=" jconfirm-box jconfirm-hilight-shake jconfirm-type-default  jconfirm-type-animated loading" role="dialog"></div>',
            defaultButtons: false,
            onContentReady: function () {

                try{
                    client.delegateEvents();

                    var jc = this;
                    //var data = self.getIndexAndSession().concat(self.getTabSearchDataFor(searchClass)).concat(self.getBigramsFormData()).concat([
                    var data = clientData.lastQueryParams.concat([
                        {name: "ngram", value: ngram} //,
                        //{name: "search_by_label", value: clientData.lastQueryParams.filter(item => {return item.name == "search_by_label"})[0].value }
                    ]);

                    $.post(app.appURL+endpoint, data, function(response){
                        self.loadResponseTweetsForNgram(data, response, jc, ngramsToGenerate, ngramLabel, client);
                    });
                }catch(err){console.log(err)}
            },
            buttons: {
                confirmAll: {
                    text: 'Confirm all',
                    btnClass: 'btn btn-outline-success',
                    action: function(e){
                        client.markBigramTweets(self, "confirmed", ngram, clientData);
                        //self.searchForTweets();
                        return false; // prevent the modal from closing
                    }
                },
                rejectAll: {
                    text: 'Reject all',
                    btnClass: 'btn btn-outline-danger',
                    action: function(){
                        client.markBigramTweets(self, "negative", ngram, clientData);
                        //self.searchForTweets();
                        return false; // prevent the modal from closing
                    }
                },
                cancel: {
                    text: 'CLOSE',
                    btnClass: 'btn-cancel'
                }
            }
        });

        return false;
    },
    loadResponseTweetsForNgram: function(data, response, jc, ngramsToGenerate, ngram, client){
        try{
            var loadMoreTweetsClass = "load-more-ngram-rel-tweets";
            var html = '<div class="ngram_rel_tweets">' + this.get_tweets_html(response, '', loadMoreTweetsClass) + '</div>';
            client.delegateEvents();
            jc.setContent(html);
           $(".jconfirm-title").text(response.tweets.total + " tweets matching the " + ngramsToGenerate + "-gram «" + ngram + "»");
            this.loadMoreTweetsButton(response, loadMoreTweetsClass);
        }catch(err){console.log(err)}
    },
    loadMoreTweetsButton: function(response, loadMoreTweetsClass){
        var loadMoreBtn = document.querySelector('.' + loadMoreTweetsClass);   //LOAD AGAIN
        var self = this;

        if(loadMoreBtn){
            loadMoreBtn.onclick = function(evt){

                evt.preventDefault();
                evt.stopImmediatePropagation();
                self.delegateEvents();

                var moreTweetsdata = [];
                moreTweetsdata.push({name: "index", value: app.session.s_index});
                moreTweetsdata.push({name: "scroll_size", value: response.tweets.scroll_size});
                moreTweetsdata.push({name: "sid",  value: response.tweets.sid});

                $.post(app.appURL+'tweets_scroll', moreTweetsdata, function(res){
                    try{
                        var html = self.get_tweets_html(res, '', loadMoreTweetsClass);
                        $(loadMoreBtn.parentElement).html(html); //LOAD AGAIN
                        self.loadMoreTweetsButton(res, loadMoreTweetsClass);

                    }catch(err){console.log(err)}
                }, 'json').fail(this.cnxError);
            }
        }
    },
    cluster_tweets: function(e){ //Button "Show tweets" inn image clusters
        e.preventDefault();
        var self = this;
        var cid = $(e.currentTarget).data("cid");
        var word = $(e.currentTarget).data("word");
        $.confirm({
                theme: 'pix-cluster-modal',
                title: 'Cluster'+cid+' Tweets',
                columnClass: 'col-md-12',
                useBootstrap: true,
                backgroundDismiss: false,
                content: 'Loading... <div class=" jconfirm-box jconfirm-hilight-shake jconfirm-type-default  jconfirm-type-animated loading" role="dialog"></div>',
                defaultButtons: false,
                onContentReady: function () {
                    var jc = this;
                    $.post(app.appURL+'cluster_search_tweets', {cid: cid, index: app.session.s_index, word: word}, function(response){
                        var html = self.get_tweets_html(response, 'static_tweet_box');
                        self.delegateEvents();
                        jc.setContent(html);
                }, 'json').fail(function() {
                        $.confirm({
                            title: 'Error',
                            boxWidth: '600px',
                            theme: 'pix-danger-modal',
                            backgroundDismiss: true,
                            content: "An error was encountered while connecting to the server, please try again.<br>Error code: tweets__cluster_tweets",
                            buttons: {
                                cancel: {
                                    text: 'CLOSE',
                                    btnClass: 'btn-cancel',
                                }
                            }
                        });
                    });
                },
                buttons: {
                    cancel: {
                        text: 'CLOSE',
                        btnClass: 'btn-cancel'
                    }
                }
            });


        return false;
    },
    displayPaginatedResults: function(response, t0, word, label){
        var html = this.get_tweets_html(response, '', 'scroll_tweets');
        this.showImageClusters(response.clusters, undefined, '.imagesClusters:visible:last', response.clusters_stats, undefined, response.total_clusters);
        this.showIndividualTweets(html, t0);
        this.showResultsStats(response.tweets.total, t0, response.keywords);
    },
    showNgramsClassification: function(classifficationData, ngrams, containerSelector, graphHeight, clientData){

        $(containerSelector).html("");
        this.renderBigramsGrid(containerSelector, graphHeight, true, "col-9");
        //var tweetsInAllBigrams = Array.from(new Set(Object.entries(ngrams).map(bigram => { return bigram[1] }).flat()));
        //var filteredTweetsInBigrams = tweets.filter(tweet => { if(tweetsInAllBigrams.indexOf(tweet._id) > -1) return tweet });

        setTimeout(() => { this.renderBigramsStats(classifficationData); }, 0); //In a new thread

        var onBubbleClick = (label, evt) => {

            var ngram = label.split(" ").join("-");
            var ngramsToGenerate = this.bigrams.formData.filter(item => {return item.name == "n-grams-to-generate"})[0].value;
            this.showNgramTweets(this.bigrams, this, ngramsToGenerate, label, ngram, "#search-results-tabs li.active a", 'search_bigrams_related_tweets');
        };
        setTimeout(() => { this.renderBigramsChart(onBubbleClick, this.bigrams, ".bigrams-graph-area:visible", ngrams, graphHeight); }, 0);

        this.updateBigramsControls(ngrams, clientData);
    },
    updateBigramsControls: function(ngrams, clientData){

        var len = Object.keys(ngrams).length;
        $(".top-bubbles-to-display:visible:last").val(len);


        //Updating the bigram's control
        var docName = "tweet";
        $.post(app.appURL+'get_mapping_spec', this.getIndexAndSession().concat([{name: "doc", value: docName}]), function(response){

            if(response == undefined || Object.keys(response).length == 0){
                $(".n-grams-to-generate:visible")[0].disabled = true;
                return;
            }

            var props = response[Object.keys(response)[0]].mappings[docName].properties;
            var sel = $(".n-grams-to-generate:visible")[0];
            if(sel) { sel.disabled = false; }

            for (var propName in props) {
                if(propName.endsWith("grams")){

                    var opt = document.createElement("option");
                        opt.value = propName.match(/\d+/)[0];
                        opt.text = propName;
                        sel.add(opt);
                }
            }

            $(".n-grams-to-generate:visible").val(clientData.lastQueryParams.find(row => row.name == "n-grams-to-generate").value);
        }, 'json');
    },
    updateTopBubblesToDisplay: function(evt){

        var onBubbleClick = (label, evt) => {

            var ngram = label.split(" ").join("-");
            var ngramsToGenerate = this.bigrams.formData.filter(item => {return item.name == "n-grams-to-generate"})[0].value;
            this.showNgramTweets(this.bigrams, this, ngramsToGenerate, label, ngram, "#search-results-tabs li.active a", 'search_bigrams_related_tweets');
        };

        this.renderBigramsChart(onBubbleClick, this.bigrams, ".bigrams-graph-area:visible", this.bigrams.bigrams, this.bigrams.graphHeight, evt.target.value);
    },
    filterElemByKey: function(key, collection){
        var res = collection.filter(item => {return item.key == key});
        return (res && res[0] && res[0].doc_count)? res[0]["doc_count"] : 0;
    },
    renderBigramsChart: function(onBubbleClick, client, domSelector, ngrams, graphHeight, maxBubblesToShow){

        this.clearNgramsGraph();
        //Set the last used values, so we don't ask for them to the backend in case the user wants small changes
        client.bigrams = ngrams;
        client.graphHeight = graphHeight;

        formatted_ngrams = ngrams.map(ngram => {  //// [ bigram[0], [bigram_confirmed, bigram_negative, bigram_unlabeled] ]
            return [
                ngram.key.split(/-+/).join(" "),
                [
                    this.filterElemByKey("confirmed", ngram.status.buckets),
                    this.filterElemByKey("negative", ngram.status.buckets),
                    this.filterElemByKey("proposed", ngram.status.buckets)
                ]
            ]
        });

        var chart = new MultiPieChart(domSelector, $(domSelector).width(), graphHeight);
        chart.onBubbleClick = onBubbleClick;
        chart.draw(formatted_ngrams); // [ bigram[0], [bigram_confirmed, bigram_negative, bigram_unlabeled] ]
    },
    renderBigramsStats: function(classifficationData){

        new BarChart(".bigrams-stats:visible", 160, 500,["confirmed", "negative", "unlabeled"], ["#28a745", "#dc3545", "#e8e8e8"], {top: 30, right: 0, bottom: 75, left: 55}).draw(classifficationData)
    },
    renderBigramsGrid: function(containerSelector, graphHeight, includeStats, colClass){
        var grid = `<div class="row" style="height: ${graphHeight}px;">`;

        if(includeStats)
            grid = grid + `<div class="col-3 bigrams-stats"></div>`;

        grid = grid + `<div class="` + colClass + ` bigrams-graph-area"></div>
                    </div>
                    <div class="row">
                        <div class="col-12 col-sm-12">
                                <form class="static_box pix-padding-20 white-bg bigrams-controls">
                                    <div class="form-row">
                                        <div class="col-md-2">
                                            <label>N-gram length</label>
                                            <select name="n-grams-to-generate" type="number" class="form-control n-grams-to-generate" value="2"></select>
                                        </div>
                                        <div class="col-md-3">
                                            <label>Max bubbles to show</label>
                                            <input name="top-bubbles-to-display" type="number" class="form-control top-bubbles-to-display" value="20" min="1" >
                                        </div>
                                        <!--<div class="col-md-2">
                                            <label for="remove-stopwords">Remove stopwords</label>
                                            <div class="">
                                                <input type="checkbox" name="remove-stopwords" data-toggle="toggle" data-on="Confirmed" data-off="Negative" data-onstyle="success" data-offstyle="danger" checked>
                                            </div>
                                        </div>
                                        <div class="col-md-2">
                                            <label for="stem-words">Stem words</label>
                                            <div class="">
                                                <div class="toggle btn btn-success" data-toggle="toggle" style="width: 113px; height: 37px;"><input name="stem-words" type="checkbox" data-toggle="toggle" data-on="Confirmed" data-off="Negative" data-onstyle="success" data-offstyle="danger" checked=""><div class="toggle-group"><label class="btn btn-success toggle-on">Confirmed</label><label class="btn btn-danger active toggle-off">Negative</label><span class="toggle-handle btn btn-light"></span></div></div>
                                            </div>
                                        </div>-->
                                    </div>
                                    <div class="mt-4 form-row">
                                        <button class="btn  btn-default regenerate-bigrams" style="width:100%">
                                            <i class="fa fa-refresh" aria-hidden="true"></i>
                                            <strong>Refresh</strong>
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>`;
        $(containerSelector).html(grid);
        $("input[data-toggle='toggle']").bootstrapToggle();

        $(".regenerate-bigrams:visible").on("click", () => {

            var data = this.getIndexAndSession().concat(this.getTabSearchData()).concat(this.getBigramsFormData());
            this.requestNgrams(data);
        })
    },
    getUniqueFormFields: function(data){

        var formData = [];
        new Set(data.map(item => {return item.name})).forEach(propName => {
            var prop = data.filter(item => {return item.name == propName});
            formData.push({"name": propName, "value": prop[prop.length-1].value })
        });
        return formData;
    },
    getTabSearchData: function(){
        return this.getTabSearchDataFor("#search-results-tabs li.active a");
    },
    getTabSearchDataFor: function(selector){
        var tabData = this.getCurrentSearchTabData(selector);
        return [
            {name: "search_by_label", value: tabData.label }
        ];
    },
    getBigramsFormData: function(){
        var formData = $('.bigrams-controls').serializeArray();

        var ngramsToGenerate = formData.filter(item => {return item.name == "n-grams-to-generate"});
        if(ngramsToGenerate.length == 0)
            formData.push({name: "n-grams-to-generate", value: "2"});

        var topBubbles = formData.filter(item => {return item.name == "top-bubbles-to-display"});
        if(topBubbles.length == 0)
            formData.push({name: "top-bubbles-to-display", value: "20"});

        return formData;
    },
    updateBigramsFormData: function(data){

        this.bigrams.formData = [
            {name: "n-grams-to-generate", value: data.filter(item => {return item.name == "n-grams-to-generate"})[0].value },
            {name: "top-bubbles-to-display", value: data.filter(item => {return item.name == "top-bubbles-to-display"})[0].value }
        ]
    },
    getIndexAndSession: function(){
        var data = $('#tweets_form').serializeArray();
        data.push({name: "index", value: app.session.s_index});
        data.push({name: "session", value:  'session_'+app.session.s_name});
        return data;
    },
    showResultsStats: function(total, t0, keywords){

        $('.loading_text:visible:last').fadeOut(0);
        $('.tweets_results').fadeIn(0);

        if(t0){
            var time = (performance.now() - t0) / 1000;
            var roundedString = time.toFixed(2);
            $('.res_time:visible:last').html(roundedString);
        }
        $('.res_num:visible:last').html(total);
        $('.res_keywords:visible:last')[0].textContent = "«" + keywords + "»";
    },
    showIndividualTweets: function(html){

        if(html.trim().length > 0) {
            $('.individual_tweets_result:visible:last').html(html);
        }
        else this.showNoTweetsFound('.individual_tweets_result:visible:last');
    },
    showImageClusters: function(clusters, word,clustersAreaSelector, clusters_stats, eid, total_clusters){
        var cbtn = "", chtml = "", state_btns="";

        console.log("TOP CLUSTERS TO PRESENT (max. in search 100): ", clusters.length, clusters);

        if(clusters && clusters.length>0){
            $(".collapse-images-title").text("Top " + clusters.length + " image-based clusters");

            if(total_clusters){
                $(".collapse-images-matching").html('<div class="pl-0 mt-1 mb-2 col-12 image_clusters_results" style="display: block;">' +
                   total_clusters + ' results matching the query (showing ' + clusters.length + ')</div>');
            }

            $.each(clusters, function(i, cluster){
                //if(i>=20){return false;}
                var cbg = "";

                if(parseInt(cluster.size)>parseInt(cluster.doc_count)){
                    cbg = 'yellow-tweet';
                }
                //if(word){
                    cbtn = '<a href="#" class="btn btn-primary btn-flat cluster_tweets" data-eid="'+eid+'" data-word="'+word+'" data-cid="'+cluster.key+'"><strong>Show tweets</strong></a>';
                    state_btns = '<div class="cluster_state_btns">';
                        state_btns += '<a href="#" class="btn btn-outline-success cluster_state" data-state="confirmed" data-cid="' + cluster.key + '"><strong>Confirmed</strong></a>';
                        state_btns += ' <a href="#" class="btn btn-outline-danger cluster_state" data-state="negative" data-cid="' + cluster.key + '"><strong>Negative</strong></a>';
                        state_btns += '</div>';
                //}
                chtml += '<div class="card p-3 '+cbg+'">'+
                    '<img class="card-img-top" src="'+app.imagesURL + app.imagesPath +'/'+ cluster.image.split("/").pop() +'" alt="">'+
                    state_btns +
                    '<div class="card-body">'+
                        '<p class="card-text">'+cluster.doc_count+' related tweets contain this image</p>'+
                        '<p class="card-text">Cluster size: '+cluster.size+'</p>'+
                        '<p class="card-text">Cluster ID: '+cluster.key+'</p>';

                if(clusters_stats){

                    let confirmed = clusters_stats[cluster.key][0];
                    let negative = clusters_stats[cluster.key][1];
                    let proposed = clusters_stats[cluster.key][2];
                    let total = confirmed + negative + proposed;
                    let confirmed_width, negative_width, proposed_width;
                    if(total == 0){
                        proposed_width = "100";
                        confirmed_width = "0";
                        negative_width= "0";
                    }
                    else {
                        proposed_width = Math.trunc(1000 * proposed / total) / 10.0;
                        confirmed_width = Math.trunc(1000 * confirmed/total)/10.0;
                        negative_width = Math.trunc(1000 * negative/total)/10.0;
                    }

                    chtml += '<div class="progress" style="border-radius: 0px;" data-toggle="tooltip" data-placement="top" title="Confirmed: '
                    +confirmed+' , Negative :'+negative+' , Unlabeled : '+proposed+'">'+
                            '<div class="progress-bar bg-success" role="progressar" style="width:'+confirmed_width+'%"></div>'+
                            '<div class="progress-bar bg-danger" role="progressar" style="width:'+negative_width+'%"></div>'+
                            '<div class="progress-bar bg-grey" role="progressar" style="width:'+proposed_width+'%"></div>'+
                        '</div>';
                }

                chtml +=    cbtn+
                    '</div>'+
                '</div>';
            });

            $(clustersAreaSelector).html(chtml);
        }
        else this.showNoImageClustersFound(".images-clusters-container:visible:last");

        $('.state_btns:visible').show();
    },
    tweet_state: function(e){
		e.preventDefault();
		var tid = $(e.currentTarget).data("tid");
		var val = $(e.currentTarget).data("val");
		var el = $(e.currentTarget).closest('.media-body').find('.t_state');

		$.post(app.appURL+'mark_tweet', {tid: tid, index: app.session.s_index, session: 'session_'+app.session.s_name, val: val}, function(response){
			var state = val;
				if(state === "confirmed"){
					state = '<span class="badge badge-success">'+state+'</span>';
				}else if (state === "negative"){
					state = '<span class="badge badge-danger">'+state+'</span>';
				}else{
					state = '<span class="badge badge-secondary">'+state+'</span>';
				}
				el.html(state);

            app.views.mabed.prototype.getClassificationStats();
		}, 'json').fail(this.cnxError);
		return false;
	},
    retweet_state: function(e){
		e.preventDefault();
		var tag = $(e.currentTarget).data("val");
		var el = $(e.currentTarget).closest('.media-body').find('.t_state');
		var text = $(e.currentTarget).closest('.media-body').find('.t_text').text();

		var jc = this.createChangingStatePopup();

		// TODO: check if this text is in the aggregations (to avoid an error if users manipulate the dom)
		$.post(app.appURL+'mark_retweets', {index: app.session.s_index, session: 'session_'+app.session.s_name, tag: tag, text: text }, function(response){
		    jc.close();
            app.views.mabed.prototype.getClassificationStats();
		}, 'json').fail(this.cnxError);
		return false;
	},
	createChangingStatePopup: function(){
	    return this.createPopupAlert('Changing tweets state', 'Please Don\'t close the page.<div class=" jconfirm-box jconfirm-hilight-shake jconfirm-type-default  jconfirm-type-animated loading" role="dialog"></div>');
	},
	createPopupAlert: function(title, message){

	    return $.confirm({
            theme: 'pix-default-modal',
            title: title,
            boxWidth: '600px',
            useBootstrap: false,
            backgroundDismiss: true,
            content: message,
            defaultButtons: false,
            buttons: {
                cancel: {
                    text: 'OK',
                    btnClass: 'btn-cancel'
                }
            }
        });
	},
    scroll_tweets: function(e){

        e.preventDefault();
        var scroll_size = $(e.currentTarget).data("scroll");
        var sid = $(e.currentTarget).data("sid");
        var btn_area = $(e.currentTarget).parent();
        var self = this;
        var data = [];
        data.push({name: "index", value: app.session.s_index});
        data.push({name: "scroll_size", value: scroll_size});
        data.push({name: "sid",  value: sid});
        $.post(app.appURL+'tweets_scroll', data, function(response){
            var html = self.get_tweets_html(response, '', 'scroll_tweets');
            btn_area.replaceWith(html);
          }, 'json').fail(this.cnxError);
        return false;
    },
    markBigramTweets: function(self, label, graphBasedLabelNgram, clientData){ //graphBasedLabelNgram may be changed (space for -, or ... when it is longer)

        var jc = self.createChangingStatePopup();

    	var data = self.getIndexAndSession().concat([
    	    {name: "ngram", value: graphBasedLabelNgram },
    	    {name: "n-grams-to-generate", value: clientData.lastQueryParams.filter(item => {return item.name == "n-grams-to-generate"})[0].value },
    	    {name: "query_label", value: clientData.lastQueryParams.filter(item => {return item.name == "search_by_label"})[0].value },
    	    {name: "word", value: clientData.lastQueryParams.filter(item => {return item.name == "word"})[0].value },
    	    {name: "new_label", value: label }
    	]);

		$.post(app.appURL+'mark_bigram_tweets', data, function(response){
            try{
                console.log(response);
                //Update the UI in case the user wants to exclude some tweets from the global tagging
                document.querySelectorAll(".ngram_rel_tweets .t_state").forEach(node => {

                    var label_status;
                    if(label == "confirmed"){
                        label_status = '<span class="badge badge-success">'+label+'</span>';
                    }else if (label == "negative"){
                        label_status = '<span class="badge badge-danger">'+label+'</span>';
                    }else{
                        label_status = '<span class="badge badge-secondary">'+label+'</span>';
                    }

                    $(node).html(label_status)
                });
            }catch(err){console.log(err)}
            //Close the "wait" message
			setTimeout(function(){
			    jc.close();
			    self.searchForTweets();
			}, 2000);
		}).fail(this.cnxError);
    	return false;
    },
    updateImageClusterStatus: function(e, data){


        function updateCluster(e,data) {
            setTimeout(function(){
                $.post(app.appURL + 'event_image_cluster_stats', data, function (response) {  // image-based cluster

                    proposed = response.filter(status => status.key == "proposed")[0].doc_count;
                    confirmed = response.filter(status => status.key == "confirmed")[0].doc_count;
                    negative = response.filter(status => status.key == "negative")[0].doc_count;

                    total = proposed + confirmed + negative;
                    proposed_width = proposed * 100 / total;
                    confirmed_width = confirmed * 100 /total;
                    negative_width =negative * 100 /total;
                    console.log(proposed_width, confirmed_width, negative_width);

                    e.querySelector(".progress-bar.bg-success").style.width = confirmed_width + "%";
                    e.querySelector(".progress-bar.bg-danger").style.width = negative_width + "%";
                    e.querySelector(".progress-bar.bg-grey").style.width = proposed_width + "%";
                });
            }, 3000);
        }

        allImages = e.currentTarget.parentElement.parentElement.parentElement.children;
        for(n = 0 ; n< allImages.length; n++)
        {
            imageCluster = allImages.item(n);
            console.log("Get the stats for image cluster", imageCluster.querySelector("div .cluster_state_btns").querySelector(".btn-outline-success").getAttribute("data-cid"));
            clusterId= imageCluster.querySelector("div .cluster_state_btns").querySelector(".btn-outline-success").getAttribute("data-cid");
            clusterData= [];
            clusterData.push(data[0]);
            clusterData.push(data[1]);
            clusterData.push(data[2]);
            clusterData.push({name: "cid", value: clusterId});
            updateCluster(imageCluster, clusterData);
        };
        //end of new code
    },
	cluster_state: function(e){
    	e.preventDefault();
    	var state = $(e.currentTarget).data("state");
    	var cid = $(e.currentTarget).data("cid");
    	var data = [];
		data.push({name: "index", value: app.session.s_index});
		data.push({name: "session", value: 'session_'+app.session.s_name});
		data.push({name: "state", value: state});
		data.push({name: "cid", value: cid});
		var jc = this.createChangingStatePopup();
		var self = this;
		$.post(app.appURL+'mark_cluster', data, function(response){
			jc.close();
            app.views.mabed.prototype.getClassificationStats();
            // TODO update all the image clusters

            self.updateImageClusterStatus(e, data);
		}).fail(function() {
            jc.close();
            $.confirm({
                title: 'Error',
                boxWidth: '600px',
                theme: 'pix-danger-modal',
                backgroundDismiss: true,
                content: "An error was encountered while connecting to the server, please try again.",
                buttons: {
                    cancel: {
                        text: 'CANCEL',
                        btnClass: 'btn-cancel'
                    }
                }
            });
        });
    	return false;
	},
    filter_tweets: function(e){
        e.preventDefault();
        $('.tweets_results').fadeOut('slow');
        $('.loading_text:visible:last').fadeIn('slow');
        var state = $(e.currentTarget).data("state");
        var t0 = performance.now();
        var data = this.getIndexAndSession();

        var self = this;

        $.post(app.appURL+'tweets_filter', data, function(response){
            self.displayPaginatedResults(response, t0, data[0].value);
        }, 'json').fail(this.cnxError);

        return false;
    },
    massive_tagging_to_state: function(e){
        e.preventDefault();

        var state = $(e.currentTarget).data("state");
        var data = this.getIndexAndSession();
            data.push({name: "state", value: state});

        //Loading message
        var jc = this.createChangingStatePopup();

        $.post(app.appURL+'mark_all_matching_tweets', data, (response)=>{

            this.searchForTweets();
            app.views.mabed.prototype.getClassificationStats();
            jc.close();

        }, 'json');

        return false;
    }
});