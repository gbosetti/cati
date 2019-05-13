// Extend this class and override the onBubbleClick method if neccesary
class BubbleWidget{

    constructor(containerSelector, index, session, graphHeight, category){

        //console.log(containerSelector, index, session);
        this.index = index;
        this.session = session;
        this.containerSelector = containerSelector;  // e.g. "#event-ngrams-tabs"
        this.graphHeight=graphHeight;
        this.category = category;
        this.onBubbleClick = (label, evt) => {
            console.log(label, evt);

            var ngram = label.split(" ").join("-");
            var formData = this.getBigramsFormData();
            console.log(formData);
            var ngramsToGenerate = formData.filter(item => {
                return item.name == "n-grams-to-generate"
            })[0];
            ngramsToGenerate = ngramsToGenerate != undefined ? ngramsToGenerate.value : 2;
            this.showNgramTweets(this.ngrams, this, ngramsToGenerate, label, ngram, "#event-ngrams-tabs li.active a", 'search_bigrams_related_tweets');
        };
    }

    showNgramTweets(clientData, client, ngramsToGenerate, ngramLabel, ngram, searchClass, endpoint){

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
                    if(client.delegateEvents)
                        client.delegateEvents();

                    var jc = this;
                    //var data = self.getIndexAndSession().concat(self.getTabSearchDataFor(searchClass)).concat(self.getBigramsFormData()).concat([
                    var data = self.getCurrentData().concat([
                        {name: "ngram", value: ngram} //,
                        //{name: "search_by_label", value: clientData.lastQueryParams.filter(item => {return item.name == "search_by_label"})[0].value }
                    ]);
                    console.log(data);

                    $.post(app.appURL+endpoint, data, function(response){
                        console.log(response);
                        self.loadResponseTweets(data, response, jc, ngramsToGenerate, ngramLabel, client);
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
    }

    get_tweets_html(response, classes, loadMoreButtonClass){

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
            html += '<div class="pix-margin-top-10"><a href="#" class="btn btn-lg btn-outline-success full_width ' + loadMoreButtonClass + '" data-scroll="'+response.tweets.scroll_size+'" data-sid="'+response.tweets.sid+'"> <strong>Load more tweets</strong> </a></div>';
        }
        return html;
    }

    loadResponseTweets(data, response, jc, ngramsToGenerate, ngram, client){
        try{
            var loadMoreTweetsClass = "load-more-ngram-rel-tweets";
            var html = '<div class="ngram_rel_tweets">' + this.get_tweets_html(response, '', loadMoreTweetsClass) + '</div>';
            if (client.delegateEvents)
                client.delegateEvents();
            jc.setContent(html);
            var self = this;
           $(".jconfirm-title").text(response.tweets.total + " tweets matching the " + ngramsToGenerate + "-gram «" + ngram + "»");
            this.loadMoreTweetsButton(response, loadMoreTweetsClass);
        }catch(err){console.log(err)}
    }

    loadMoreTweetsButton(response, loadMoreTweetsClass){
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
    }

    render(ngrams){

        $(this.containerSelector).html("");

        if ($.isEmptyObject(ngrams)) {
            console.log("Empty");
            this.showNoBigramsFound(this.containerSelector);
            return;
        }

        console.log("FILTERED!!!", ngrams);

        var chart = new MultiPieChart(this.containerSelector, $(this.containerSelector).width(), this.graphHeight);
        chart.onBubbleClick = this.onBubbleClick;
        chart.draw(ngrams);
    }

    showNoBigramsFound(){
        $(this.containerSelector).html("Sorry, no bigrams were found under this criteria.");
    }

    getCurrentData(){

        var data = [];
        data.push({name: "index", value: this.index });
        data.push({name: "session", value: this.session });

        var tabData = {name: "search_by_label", value: this.category }; //this.getTabSearchDataFor(this.selector + " li.active a");
        var bigramsData = this.getBigramsFormData();

        return data.concat(tabData).concat(bigramsData);
    }

    /*getCurrentSearchTabData(selector){
        var tab = document.querySelector(selector);
        return {
            label: tab.getAttribute("tag"),
            target: document.querySelector(tab.target)
        };
    }

    getTabSearchDataFor(selector){
        var tabData = this.getCurrentSearchTabData(selector);
        return [
            {name: "search_by_label", value: tabData.label }
        ];
    }*/

    getBigramsFormData(){
        var formData = $('.bigrams-controls').serializeArray();

        var ngramsToGenerate = formData.filter(item => {return item.name == "n-grams-to-generate"});
        if(ngramsToGenerate.length == 0)
            formData.push({name: "n-grams-to-generate", value: "2"});

        var topBubbles = formData.filter(item => {return item.name == "top-bubbles-to-display"});
        if(topBubbles.length == 0)
            formData.push({name: "top-bubbles-to-display", value: "20"});

        return formData;
    }
}