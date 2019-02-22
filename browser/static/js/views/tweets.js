app.views.tweets = Backbone.View.extend({
    template: _.template($("#tpl-page-tweets").html()),
    events: {
        'submit #tweets_form': 'tweets_submit',
        'click .tweet_state': 'tweet_state',
        'click .cluster_tweets': 'cluster_tweets',
        'click .scroll_tweets': 'scroll_tweets',
        'click .cluster_state': 'cluster_state',
        'click .btn_filter': 'filter_tweets',
        'click .all_tweets_state': 'all_tweets_state',
        'click #search_not_labeled': 'search_not_labeled',
        'change #top-bubbles-to-display': 'updateTopBubblesToDisplay'
    },
    initialize: function() {

        this.bigrams = { //Session data for the bigrams
            bigrams: undefined,
            tweets: undefined,
            graphHeight: undefined,
            formData: this.getBigramsDefaultFormData()
        };

        this.render();
        var handler = _.bind(this.render, this);
        var self = this;
        $(document).on("click","body .tweet_state",function(e){
			self.tweet_state(e);
		});
		$(document).on("click","#search-accordion .card-header",function(e){
			if(e.target.tagName.toLocaleLowerCase() == "div")
			    e.target.querySelector("a").click();
		});
    },
    render: function(){
        var html = this.template();
        this.$el.html(html);
        this.delegateEvents();
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

      $('#tweets_results').fadeOut('slow');
      $('.loading_text').fadeIn('slow');

      this.displayResultsArea();

      var data = this.getSearchFormData();
      this.requestTweets(data);
      this.requestBigrams(data.concat(this.bigrams.formData));

      return false;
    },
    search_not_labeled: function(e){
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
        $('#tweets_results').fadeOut('slow');
        $('.loading_text').fadeIn('slow');
        var t0 = performance.now();
        var data = this.getSearchFormData();
        data.push({name: "state", value: "proposed"});

        var self = this;
        $.post(app.appURL+'search_for_tweets_state', data, function(response){

            self.display_tweets(response, t0, data[0].value);
        }, 'json').fail(self.cnxError);

        self.requestBigrams(data.concat(this.bigrams.formData));

        return false;
    },
    displayResultsArea: function(){
        document.querySelector("#search-accordion").hidden = false;
    },
    requestTweets: function(data){

        var t0 = performance.now();

        //First clean the previous results
        $('#imagesClusters').html("");
        this.showLoadingMessage('imagesClusters', 400);

        $('#tweets_result').html("");
        this.showLoadingMessage('tweets_result', 400);

        var self = this;
        $.post(app.appURL+'search_for_tweets', data, function(response){
            self.displayPaginatedResults(response, t0, data[0].value);
        }, 'json').fail(self.cnxError);
    },
    requestBigrams: function(data){
        var containerId = "ngrams-search-classif";
        this.showLoadingMessage(containerId, 677);
        var self = this;
        console.log("requestBigrams's data", data);

        this.bigrams.formData = data;

        $.post(app.appURL+'bigrams_with_higher_ocurrence', data, (response) => {
            //check if there are any bigrams
            if($.isEmptyObject(response.bigrams))
                self.showNoBigramsFound(containerId);
            else self.showBigramsClassification(response.bigrams, response.tweets.hits.hits, containerId, 500);

        }, 'json').fail(function(err){
            this.clearNgramsGraph();
            console.log(err);
            self.cnxError(err);
        });
    },
    clearNgramsGraph: function(){
        $("#bigrams-graph-area").html("");
    },
    showNoBigramsFound: function(containedId){
        $("#" + containedId).html("Sorry, no bigrams were found.");
    },
    showLoadingMessage: function(containerId, height){

        $("#" + containerId).html("");
        var spinner = document.createElement("div");
            spinner.className = "loader";

        var spinnerFrame = document.createElement("div");
            spinnerFrame.className = "card-columns";
            spinnerFrame.style.width = "120px";
            spinnerFrame.style.margin = "0 auto";
            if(height)
                spinnerFrame.style.height = height + "px";
            spinnerFrame.style["padding-top"] = "150px";
            spinnerFrame.appendChild(spinner);

        document.querySelector("#" + containerId).appendChild(spinnerFrame);
    },
    cnxError: function(err) {
        $('.loading_text').fadeOut('slow');
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
    get_tweets_html: function(response, classes, cid){
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
                        imgs += '<a href="'+app.imagesURL+app.session.s_index+'/'+tweet._source.id_str+"_"+i+'.'+ext+'" target="_blank"><img style="margin:2px;max-height:150px;width:auto;" src="'+app.imagesURL+app.session.s_index+'/'+tweet._source.id_str+"_"+i+'.'+ext+'"></a>'
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
                          name: tweet._source.user.name,
                          screen_name: tweet._source.user.screen_name,
                          created_at: tweet._source.created_at,
                          link: tweet._source.link,
                          text:  tweet._source.text,
                          classes: t_classes,
                          images: imgs,
                            state: state
                        });
        });
        if(response.tweets.scroll_size>0){
            html += '<div class="pix-margin-top-10"><a href="#" class="btn btn-lg btn-outline-success full_width scroll_tweets" data-scroll="'+response.tweets.scroll_size+'" data-sid="'+response.tweets.sid+'"> <strong>Load more tweets</strong> </a></div>';
        }
        return html;
    },
    showBigramTweets: function(title, relatedTweets){

        var self = this;
        $.confirm({
            theme: 'pix-cluster-modal',
            title: title,
            columnClass: 'col-md-12',
            useBootstrap: true,
            backgroundDismiss: false,
            content: 'Loading... <div class=" jconfirm-box jconfirm-hilight-shake jconfirm-type-default  jconfirm-type-animated loading" role="dialog"></div>',
            defaultButtons: false,
            onContentReady: function () {
                self.delegateEvents();
                // response.tweets.results
                var response = {"tweets": {"results": relatedTweets}};
                this.setContent("<div id='bigram_rel_tweets'>" + self.get_tweets_html(response, '') + "</div>");
            },
            buttons: {
                confirmAll: {
                    text: 'Confirm all',
                    btnClass: 'btn btn-outline-success',
                    action: function(e){
                        self.markBigramTweets("confirmed", relatedTweets);
                        return false; // prevent the modal from closing
                    }
                },
                rejectAll: {
                    text: 'Reject all',
                    btnClass: 'btn btn-outline-danger',
                    action: function(){
                        self.markBigramTweets("negative", relatedTweets);
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
                        var html = self.get_tweets_html(response, 'static_tweet_box', cid);
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
    displayPaginatedResults: function(response, t0, word){
        var html = '';
        html += '<div class="col-12 pix-padding-top-30 pix-padding-bottom-30">\n' +
            '                    <a class="btn btn-lg btn-success pix-white fly shadow scale btn_filter" data-state="confirmed" href="#" role="button"><strong>Confirmed</strong></a>\n' +
            '                    <a class="btn btn-lg btn-danger pix-white fly shadow scale btn_filter" data-state="negative" href="#" role="button"><strong>Negative</strong></a>\n' +
            '                    <a class="btn btn-lg btn-primary pix-white fly shadow scale btn_filter" data-state="proposed" href="#" role="button"><strong>Proposed</strong></a>\n' +
            '              </div>';

        html += this.get_tweets_html(response, '');
        this.showImageClusters(response.clusters, word);
        this.showIndividualTweets(html, t0);
        this.showResultsStats(response.tweets.total, t0);
    },
    showBigramsClassification: function(bigrams, tweets, containedId, graphHeight){

        var graphArea = $("#" + containedId);
            graphArea.html("");

        this.renderBigramsGrid(containedId);
        var tweetsInAllBigrams = Array.from(new Set(Object.entries(bigrams).map(bigram => { return bigram[1] }).flat()));
        var filteredTweetsInBigrams = tweets.filter(tweet => { if(tweetsInAllBigrams.indexOf(tweet._id) > -1) return tweet });

        console.log("bigrams", bigrams);

        setTimeout(() => { this.renderBigramsChart("#bigrams-graph-area", bigrams, tweets, graphHeight); }, 0);
        setTimeout(() => { this.renderBigramsStats(filteredTweetsInBigrams, tweets); }, 0); //In a new thread
        this.updateBigramsControls(bigrams);
    },
    updateBigramsControls: function(bigrams){

        var len = Object.keys(bigrams).length;
        $("#top-bubbles-to-display").attr({"max": len});
        $("#top-bubbles-to-display").val(len);

        console.log(this.bigrams.formData);
        $("#n-grams-to-generate").val(this.bigrams.formData.find(row => row.name == "n-grams-to-generate").value);
    },
    updateTopBubblesToDisplay: function(evt){

        this.renderBigramsChart("#bigrams-graph-area", this.bigrams.bigrams, this.bigrams.tweets, this.bigrams.graphHeight, evt.target.value);
    },
    renderBigramsChart: function(domSelector, bigrams, tweets, graphHeight, maxBubblesToShow){

        this.clearNgramsGraph();

        //Set the last used values, so we don't ask for them to the backend in case the user wants small changes
        this.bigrams.bigrams = bigrams;
        this.bigrams.tweets = tweets;
        this.bigrams.graphHeight = graphHeight;

        var bigramsAsFilteredOrderedArray = maxBubblesToShow? Object.entries(bigrams).sort(function(a, b){return (new Set(a[1]).size > new Set(b[1]).size? -1 : 1) }).splice(0,maxBubblesToShow) : Object.entries(bigrams);
        var dta = bigramsAsFilteredOrderedArray.map(bigram => {

            var bigramMatchingTweets = tweets.filter(tweet => { return bigram[1].includes(tweet["_id"]) });
            var bigram_confirmed = bigramMatchingTweets.filter(tweet => { return tweet._source['session_'+app.session.s_name] == "confirmed" }).length;
            var bigram_negative = bigramMatchingTweets.filter(tweet => { return tweet._source['session_'+app.session.s_name] == "negative" }).length;
            var bigram_unlabeled = bigramMatchingTweets.filter(tweet => { return tweet._source['session_'+app.session.s_name] == "proposed" }).length;

            return [ bigram[0], [bigram_confirmed, bigram_negative, bigram_unlabeled] ]
        });

        var chart = new MultiPieChart(domSelector, $(domSelector).width(), graphHeight);
        chart.onBubbleClick = (event) => {
            for (var bigram in bigrams) {
                if (bigram == event.label){
                    var matchingTweets = tweets.filter(tweet => { return bigrams[bigram].includes(tweet["_id"]) });
                    this.showBigramTweets("Tweets associated to the bigram «" + event.label + "»", matchingTweets);
                    return true;
                }
            }
        };
        chart.draw(dta);
    },
    renderBigramsStats: function(filteredTweetsInBigrams, tweets){

        var query_confirmed = tweets.filter(tweet => { return tweet._source['session_'+app.session.s_name] == "confirmed" }).length;
        var query_negative = tweets.filter(tweet => { return tweet._source['session_'+app.session.s_name] == "negative" }).length;
        var query_unlabeled = tweets.filter(tweet => { return tweet._source['session_'+app.session.s_name] == "proposed" }).length;

        var bigrams_confirmed = filteredTweetsInBigrams.filter(tweet => { return tweet._source['session_'+app.session.s_name] == "confirmed" }).length;
        var bigrams_negative = filteredTweetsInBigrams.filter(tweet => { return tweet._source['session_'+app.session.s_name] == "negative" }).length;
        var bigrams_unlabeled = filteredTweetsInBigrams.filter(tweet => { return tweet._source['session_'+app.session.s_name] == "proposed" }).length;

        var data = [
              { label: "Query", confirmed: query_confirmed, negative: query_negative, unlabeled: query_unlabeled },
              { label: "Bigrams", confirmed: bigrams_confirmed, negative: bigrams_negative, unlabeled: bigrams_unlabeled }
            ];

        new BarChart("#bigrams-stats", 160, 500,["confirmed", "negative", "unlabeled"], ["#28a745", "#dc3545", "#e8e8e8"], {top: 30, right: 0, bottom: 75, left: 55}).draw(data)
    },
    renderBigramsGrid: function(containedId){
        var grid = `<div class="row">
                        <div class="col-3" id="bigrams-stats"></div>
                        <div class="col-9" id="bigrams-graph-area"></div>
                    </div>
                    <div class="row">
                        <div class="col-12 col-sm-12">
                                <form id="bigrams-controls" class="static_box pix-padding-20 white-bg">
                                    <div class="form-row">
                                        <div class="col-md-2">
                                            <label for="n-grams-to-generate">N-gram length</label>
                                            <input id="n-grams-to-generate" name="n-grams-to-generate" type="number" class="form-control" value="2">
                                        </div>
                                        <!--<div class="col-md-2">
                                            <label for="min-tweets-in-bigram">Min tweets by n-gram</label>
                                            <input id="min-tweets-in-bigram" type="number" class="form-control" value="25">
                                        </div>-->
                                        <div class="col-md-2">
                                            <label for="top-bubbles-to-display">Max bubbles to show</label>
                                            <input id="top-bubbles-to-display" name="top-bubbles-to-display" type="number" class="form-control" value="10" min="1" max="10">
                                        </div>
                                        <!--<div class="col-md-2">
                                            <label for="remove-stopwords">Remove stopwords</label>
                                            <div class="">
                                                <div class="toggle btn btn-success" data-toggle="toggle" style="width: 100%; height: 37px;"><div class="toggle btn btn-success" data-toggle="toggle" style="width: 113px; height: 37px;"><input id="remove-stopwords" type="checkbox" data-toggle="toggle" data-on="Confirmed" data-off="Negative" data-onstyle="success" data-offstyle="danger" checked=""><div class="toggle-group"><label class="btn btn-success toggle-on">Confirmed</label><label class="btn btn-danger active toggle-off">Negative</label><span class="toggle-handle btn btn-light"></span></div></div><div class="toggle-group"><label class="btn btn-success toggle-on">Confirmed</label><label class="btn btn-danger active toggle-off">Negative</label><span class="toggle-handle btn btn-light"></span></div></div>
                                            </div>
                                        </div>
                                        <div class="col-md-2">
                                            <label for="stem-words">Stem words</label>
                                            <div class="">
                                                <div class="toggle btn btn-success" data-toggle="toggle" style="width: 113px; height: 37px;"><input id="stem-words" type="checkbox" data-toggle="toggle" data-on="Confirmed" data-off="Negative" data-onstyle="success" data-offstyle="danger" checked=""><div class="toggle-group"><label class="btn btn-success toggle-on">Confirmed</label><label class="btn btn-danger active toggle-off">Negative</label><span class="toggle-handle btn btn-light"></span></div></div>
                                            </div>
                                        </div>-->
                                    </div>
                                    <div class="mt-4 form-row">
                                        <button id="regenerate-bigrams" class="btn  btn-default" style="width:100%">
                                            <i class="fa fa-refresh" aria-hidden="true"></i>
                                            <strong>Refresh</strong>
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>`;
        $("#" + containedId).html(grid);

        $("#bigrams-controls").on("click", "#regenerate-bigrams", () => {
            this.bigrams.formData = this.getBigramsFormData();
            this.requestBigrams(this.getSearchFormData().concat(this.bigrams.formData));
        })
    },
    getBigramsFormData: function(){
        return $('#bigrams-controls').serializeArray();
    },
    getBigramsDefaultFormData: function(){
        return [
            {name: "n-grams-to-generate", value: "2"},
            {name: "top-bubbles-to-display", value: "10"}
        ];
    },
    getSearchFormData: function(){
        var data = $('#tweets_form').serializeArray();
        data.push({name: "index", value: app.session.s_index});
        data.push({name: "session", value:  'session_'+app.session.s_name});
        return data;
    },
    formatDataForHeatmap: function(ngrams){
        //TODO: for performance reasons, we should move this to the backend

        try{

            xLabels = Array.from(new Set(ngrams.map(ngram => {  // "Wednesday", "Tuesday", "Thursday", "Monday", "Friday"
              return ngram[0][0]
            }))).sort().reverse();

            yLabels = Array.from(new Set(ngrams.map(ngram => {  // AF MN
              return ngram[0][1]
            }))).sort();

            var matrix = []; //This will behave as an object rather than a matrix. We need to create it anyway in order to fill the blank spaces.

            for (var i = 0; i < yLabels.length; i++) {
              matrix[i] = new Array(xLabels.length).fill(0);

              for (var j = 0; j < xLabels.length; j++) {
                 ngrams.forEach(row => {
                        if(row[0][0] == xLabels[j] && row[0][1] == yLabels[i]){
                            matrix[i][j] = row[1];
                    }
                 });
              }
            }
            return { "matrix": matrix, "xLabels": xLabels, "yLabels": yLabels };
        }catch(err){console.log(err)}
    },
    showResultsStats: function(total, t0){

        if(t0){
            var t1 = performance.now();
            var time = (t1 - t0) / 1000;
            var roundedString = time.toFixed(2);
            $('#res_num').html(total);
            $('#res_time').html(roundedString);
        }
    },
    showIndividualTweets: function(html){

        $('#tweets_result').html(html);
        $('.loading_text').fadeOut('slow');
        $('#tweets_results').fadeIn('slow');
    },
    showImageClusters: function(clusters, word){
        var cbtn = "", chtml = "", state_btns="";

        if(clusters){
            $.each(clusters, function(i, cluster){
                if(i>=20){return false;}
                var cbg = "";
                if(parseInt(cluster.size)>parseInt(cluster.doc_count)){
                    cbg = 'yellow-tweet';
                }
                if(word){
                    cbtn = '<a href="#" class="btn btn-primary btn-flat cluster_tweets" data-word="'+word+'" data-cid="'+cluster.key+'"><strong>Show tweets</strong></a>';
                    state_btns = '<div class="cluster_state_btns">';
                        state_btns += '<a href="#" class="btn btn-outline-success cluster_state" data-state="confirmed" data-cid="' + cluster.key + '"><strong>Confirmed</strong></a>';
                        state_btns += ' <a href="#" class="btn btn-outline-danger cluster_state" data-state="negative" data-cid="' + cluster.key + '"><strong>Negative</strong></a>';
                        state_btns += '</div>';
                }
                chtml += '<div class="card p-3 '+cbg+'">'+
                    '<img class="card-img-top" src="'+app.imagesURL+app.session.s_index+'/'+cluster.image+'" alt="">'+
                    state_btns +
                    '<div class="card-body">'+
                        '<p class="card-text">'+cluster.doc_count+' related tweets contain this image</p>'+
                        '<p class="card-text">Cluster size: '+cluster.size+'</p>'+
                        '<p class="card-text">Cluster ID: '+cluster.key+'</p>'+
                        cbtn+
                    '</div>'+
                '</div>';
            });
            $('#imagesClusters').html(chtml);
        }

        $('.state_btns').show();
    },
    tweet_state: function(e){
		e.preventDefault();
		var tid = $(e.currentTarget).data("tid");
		var val = $(e.currentTarget).data("val");
		var el = $(e.currentTarget).closest('.media-body').find('.t_state');
		$.post(app.appURL+'mark_tweet', {tid: tid, index: app.session.s_index, session: app.session.s_name, val: val}, function(response){
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
		}, 'json').fail(function() {
                        $.confirm({
                            title: 'Error',
                            boxWidth: '600px',
                            theme: 'pix-danger-modal',
                            backgroundDismiss: true,
                            content: "An error was encountered while connecting to the server, please try again.<br>Error code: tweets__tweet_state",
                            buttons: {
                                cancel: {
                                    text: 'CLOSE',
                                    btnClass: 'btn-cancel',
                                }
                            }
                        });
                    });
		return false;
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
            var html = self.get_tweets_html(response, '');
            btn_area.replaceWith(html);
          }, 'json').fail(this.cnxError);
        return false;
    },
    markBigramTweets: function(label, relatedTweets){

        var jc = $.confirm({
            theme: 'pix-default-modal',
            title: 'Changing tweets state',
            boxWidth: '600px',
            useBootstrap: false,
            backgroundDismiss: false,
            content: 'Please Don\'t close the page.<div class=" jconfirm-box jconfirm-hilight-shake jconfirm-type-default  jconfirm-type-animated loading" role="dialog"></div>',
            defaultButtons: false,
            buttons: {
                cancel: {
                    text: 'OK',
                    btnClass: 'btn-cancel'
                }
            }
        });

        var tweetIds = relatedTweets.map(tweet => { return tweet._id });

    	var data = [];
		data.push({name: "index", value: app.session.s_index});
		data.push({name: "session", value: app.session.s_name});
		data.push({name: "label", value: label});
		data.push({name: "tweet_ids", value: JSON.stringify(tweetIds)});

		$.post(app.appURL+'mark_bigram_tweets', data, function(response){

            //Update the labels in the dataset, so if the user closes and open the modal again the values will be up to date.
		    relatedTweets.forEach(tweet => {
                tweet._source['session_'+app.session.s_name] = label;
            });

            try{

                //Update the UI in case the user wants to exclude some tweets from the global tagging
                document.querySelectorAll("#bigram_rel_tweets .t_state").forEach(node => {

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
			jc.close();

		}).fail(function(e) {
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
	cluster_state: function(e){
    	e.preventDefault();
    	var state = $(e.currentTarget).data("state");
    	var cid = $(e.currentTarget).data("cid");
    	var data = [];
		data.push({name: "index", value: app.session.s_index});
		data.push({name: "session", value: app.session.s_name});
		data.push({name: "state", value: state});
		data.push({name: "cid", value: cid});
		var jc = $.confirm({
				theme: 'pix-default-modal',
				title: 'Changing tweets state',
				boxWidth: '600px',
				useBootstrap: false,
				backgroundDismiss: false,
				content: 'Please Don\'t close the page.<div class=" jconfirm-box jconfirm-hilight-shake jconfirm-type-default  jconfirm-type-animated loading" role="dialog"></div>',
				defaultButtons: false,
				buttons: {
					cancel: {
						text: 'OK',
						btnClass: 'btn-cancel'
					}
				}
			});
		$.post(app.appURL+'mark_cluster', data, function(response){
			jc.close();
            app.views.mabed.prototype.getClassificationStats();
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
        $('#tweets_results').fadeOut('slow');
        $('.loading_text').fadeIn('slow');
        var state = $(e.currentTarget).data("state");
        var t0 = performance.now();
        var data = this.getSearchFormData();

        var self = this;

        $.post(app.appURL+'tweets_filter', data, function(response){
            self.displayPaginatedResults(response, t0, data[0].value);
        }, 'json').fail(self.cnxError);

        return false;
    },
    all_tweets_state: function(e){
        e.preventDefault();
        var state = $(e.currentTarget).data("state");
        var data = this.getSearchFormData();
            data.push({name: "state", value: state});
        var force = document.getElementById('force_all');

             var jc = $.confirm({
                theme: 'pix-default-modal',
                title: 'Changing tweets state',
                boxWidth: '600px',
                useBootstrap: false,
                backgroundDismiss: false,
                content: 'Please Don\'t close the page.<div class=" jconfirm-box jconfirm-hilight-shake jconfirm-type-default  jconfirm-type-animated loading" role="dialog"></div>',
                defaultButtons: false,
                buttons: {
                    cancel: {
                        text: 'OK',
                        btnClass: 'btn-cancel'
                    }
                }
            });

        if (force.checked){
            $.post(app.appURL+'mark_search_tweets_force', data, function(response){
                jc.close();
                $.confirm({
                    theme: 'pix-default-modal',
                    title: 'Changing tweets state',
                    boxWidth: '600px',
                    useBootstrap: false,
                    backgroundDismiss: false,
                    content: 'Please click the search button again to refresh the result!',
                    defaultButtons: false,
                    buttons: {
                        cancel: {
                            text: 'OK',
                            btnClass: 'btn-cancel'
                        }
                    }
                });
            }, 'json');
        }else{


            $.post(app.appURL+'mark_search_tweets', data, function(response){
                jc.close();
                    $.confirm({
                    theme: 'pix-default-modal',
                    title: 'Changing tweets state',
                    boxWidth: '600px',
                    useBootstrap: false,
                    backgroundDismiss: false,
                    content: 'Please click the search button again to refresh the result!',
                    defaultButtons: false,
                    buttons: {
                        cancel: {
                            text: 'OK',
                            btnClass: 'btn-cancel'
                        }
                    }
                });
            }, 'json');
        }


        return false;
    }
});
