app.views.client = Backbone.View.extend({
    template: _.template($("#tpl-page-2").html()),
    events: {
        'click .event_word_btn': 'timeline_btn',
        'click #reset_impact': 'reset_impact',
        'click .tl_options_btn': 'mark_event',
        'click .cluster_tweets': 'cluster_tweets',
        'click .scroll_tweets': 'scroll_tweets',
        'click .cluster_state': 'cluster_state',
        'click .btn_filter': 'filter_tweets',
        'click .event-tweets-tab': 'filter_tweets_matching_tab',
        'click .event-ngrams-tab': 'filter_ngrams_matching_tab'
    },
    initialize: function () {
        this.ngrams = { //Session data for the ngrams
            bigrams: undefined,
            tweets: undefined,
            graphHeight: undefined,
            formData: []
        };
        //var handler = _.bind(this.render, this);
        var self = this;
        $(document).on("click", "body .tweet_state", function (e) { // Search tweets
            self.tweet_state(e);
        });
    },
    render: async function () {
        var html = this.template({});
        this.$el.html(html);
        this.delegateEvents();
        $('#timeline_div').html('<div id="timeline-embed" style="width: 100%; height: 800px;box-shadow: 0 4px 2px -2px rgba(0,0,0,0.2)"></div>');
        await app.views.mabed.prototype.setSessionTopBar();
        app.views.mabed.prototype.getClassificationStats();

        this.load_timeline(); //This method loads also the tweets and ngrams
        this.load_impact();

        this.enableAccordion();
        return this;
    },
    enableAccordion: function () {
        $(".event-accordion-shrink").on("click", evt => {

            if (evt.target.tagName.toLocaleLowerCase() == "span")
                return;

            if (evt.target.classList.contains("event-accordion-shrink")) {
                evt.target.classList.remove("event-accordion-shrink");
                evt.target.classList.add("event-accordion-expand");
                $(evt.target.parentNode.nextElementSibling).hide();
            } else {
                evt.target.classList.add("event-accordion-shrink");
                evt.target.classList.remove("event-accordion-expand");
                $(evt.target.parentNode.nextElementSibling).show();
            }

            evt.preventDefault();
            evt.stopImmediatePropagation();
        });
    },
    load_ngrams: function (eventId) {

        this.lastNgramsEventId = eventId;

        var event = app.eventsCollection.get({cid: this.lastNgramsEventId}).toJSON(); // JSON.stringify(
        var data = app.views.tweets.prototype.getIndexAndSession().concat(
            app.views.tweets.prototype.getTabSearchDataFor("#event-ngrams-tabs li.active a")).concat(
            [{name: "event", value: JSON.stringify(event)}]).concat(
            app.views.tweets.prototype.getBigramsFormData());

        this.request_ngrams(data).then(response => {

            var containerSelector = ".event-ngrams";
            this.ngrams.lastQueryParams = data;

            console.log("NGRAMS:", response.ngrams);

            if ($.isEmptyObject(response.ngrams)) {
                app.views.tweets.prototype.showNoBigramsFound(containerSelector);
            } else {

                $(containerSelector).html("");
                app.views.tweets.prototype.renderBigramsGrid(containerSelector, 600, false, "col-12");
                app.views.tweets.prototype.updateBigramsControls(response.ngrams, this.ngrams);

                var onBubbleClick = (label, evt) => {

                    var ngram = label.split(" ").join("-");
                    var ngramsToGenerate = this.ngrams.formData.filter(item => {
                        return item.name == "n-grams-to-generate"
                    })[0];
                    ngramsToGenerate = ngramsToGenerate != undefined ? ngramsToGenerate.value : 2;
                    app.views.tweets.prototype.showNgramTweets(this.ngrams, this, ngramsToGenerate, label, ngram, "#event-ngrams-tabs li.active a", 'search_event_bigrams_related_tweets');
                };

                app.views.tweets.prototype.renderBigramsChart(onBubbleClick, this.ngrams, ".bigrams-graph-area", response.ngrams, 600);
            }

            $(".regenerate-bigrams").prop("disabled", true);
        });

    },
    markBigramTweets: function (self, label, graphBasedLabelNgram, clientData) { //graphBasedLabelNgram may be changed (space for -, or ... when it is longer)

        var jc = self.createChangingStatePopup();

        var data = clientData.lastQueryParams.concat([
            {name: "ngram", value: graphBasedLabelNgram},
            {
                name: "query_label", value: clientData.lastQueryParams.filter(item => {
                    return item.name == "search_by_label"
                })[0].value
            },
            {name: "new_label", value: label}
        ]);
        console.log("data", data);

        var client = this;

        $.post(app.appURL + 'mark_event_ngram_tweets', data, function (response) {
            try {
                console.log(response);
                //Update the UI in case the user wants to exclude some tweets from the global tagging
                document.querySelectorAll(".ngram_rel_tweets .t_state").forEach(node => {

                    var label_status;
                    if (label == "confirmed") {
                        label_status = '<span class="badge badge-success">' + label + '</span>';
                    } else if (label == "negative") {
                        label_status = '<span class="badge badge-danger">' + label + '</span>';
                    } else {
                        label_status = '<span class="badge badge-secondary">' + label + '</span>';
                    }

                    $(node).html(label_status)
                });
            } catch (err) {
                console.log(err)
            }
            //Close the "wait" message
            jc.close();
            //self.searchForTweets();
            client.load_ngrams(client.lastNgramsEventId);
        }).fail(this.cnxError);
        return false;
    },
    request_ngrams: function (data) {

        return new Promise((resolve, reject) => {
            $.post(app.appURL + 'event_ngrams_with_higher_ocurrence', data, (response) => {
                resolve(response)
            }, 'json').fail(function (err) {
                console.log(err);
                reject(err)
            });
        });
    },
    load_timeline: function () {
        var self = this;
        let session = "session_"+app.session.s_name;
        app.eventsCollection.get_timeline_events().then(data => {

            if ($('#timeline-embed').length) {

                timeline = new TL.Timeline('timeline-embed', data, {
                    timenav_height: 260,
                    marker_height_min: 40
                });

                if(data.events.length==0){
                    $(".event_results_area").html("");
                    return;
                }
                var s_ev = app.eventsCollection.get({cid: timeline.config.events[0].unique_id}).toJSON();
                self.currentClusterId = timeline.config.events[0].unique_id;
                var t0 = performance.now();
                self.eventTweetsParams = {obj: JSON.stringify(s_ev), index: app.session.s_index, session: session};

                $.post(app.appURL + 'event_tweets', self.eventTweetsParams, function (response) {
                    try {
                        self.display_tweets(response, t0, timeline.config.events[0].unique_id);
                        self.load_ngrams(timeline.config.events[0].unique_id);
                    } catch (err) {
                        console.log(err)
                    }
                }, 'json').fail(function (err) {
                    console.log(err);
                });

                timeline.on('change', function (data) {
                    try {
                        var ev = app.eventsCollection.get({cid: data.unique_id}).toJSON();
                        self.currentClusterId = data.unique_id;
                        self.load_impact(ev.main_term);
                        $('.tweets_results').fadeOut('slow');
                        $('.loading_text').fadeIn('slow');
                        var t0 = performance.now();
                        self.eventTweetsParams = {obj: JSON.stringify(ev), index: app.session.s_index, session: session};

                        $.post(app.appURL + 'event_tweets', self.eventTweetsParams, function (response) {
                            try {
                                self.display_tweets(response, t0, data.unique_id);
                                self.load_ngrams(data.unique_id);
                            } catch (err) {
                                console.log(err)
                            }
                        }, 'json');
                    } catch (err) {
                        console.log(err)
                    }
                });
            }
        });
    },
    reset_impact: function (e) {
        e.preventDefault();
        this.load_impact();
        return false;
    },
    load_impact: function (event) {

        if (app.session.impact_data == undefined){ return; }
        if ($('#chartDiv').length) {

            $('#chartDiv').fadeOut('slow');

            var event_impact = JSON.parse(app.session.impact_data);
            if (event) {
                $.each(event_impact, function (i, e) {
                    if (e.key != event) {
                        var opacity = (Math.floor(Math.random() * 10) + 1) * 0.1;
                        e.color = 'rgba(0,0,0,' + opacity + ')';
                    }
                });
            }
            var chart;
            nv.addGraph(function () {
                chart = nv.models.stackedAreaChart()
                    .useInteractiveGuideline(true)
                    .x(function (d) {
                        return d[0]
                    })
                    .y(function (d) {
                        return d[1]
                    })
                    .controlLabels({stacked: "Stacked"});

                chart.yAxis.scale().domain([0, 20]);
                chart.xAxis.tickFormat(function (d) {
                    return d3.time.format('%x')(new Date(d))
                });
                chart.yAxis.tickFormat(d3.format(',.4f'));
                chart.height(300);

                chart.legend.vers('furious');

                chart.showControls(false);
                $('#chartDiv').html('<svg id="chart1" style="height: 300px;"></svg>')

                console.log("event_impact:", event_impact);
                var output = d3.select('#chart1')
                    .datum(event_impact)
                    .call(chart);
                nv.utils.windowResize(chart.update);
                return chart;
            });
            $('#chartDiv').fadeIn('slow');
        }

    },
    timeline_btn: function (e) {
        e.preventDefault();
        var self = this;
        var word = $(e.currentTarget).data("value");
        $('.tweets_results').fadeOut('slow');
        $('.loading_text').fadeIn('slow');
        var t0 = performance.now();
        $.post(app.appURL + 'tweets', {word: word, index: app.session.s_index}, function (response) {
            self.display_tweets(response, t0);
        }, 'json');

        return false;
    },
    mark_event: function (e) {
        e.preventDefault();
        console.log("Updating event values (mark_event)");
        var self = this;
        var targetEvent = {cid: $(e.currentTarget).data("cid")};
        var s_ev = JSON.stringify(app.eventsCollection.get(targetEvent));
        var data = [];
        data.push({name: "index", value: app.session.s_index});
        data.push({name: "session", value: app.session.s_name});
        data.push({name: "event", value: s_ev});
        data.push({name: "labeling_class", value: $(e.currentTarget).data("status")});

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

        $.post(app.appURL + 'massive_tag_event_tweets', data, function (response) { //mark_event
            jc.close();
            app.views.mabed.prototype.getClassificationStats();
        }, 'json');
        return false;
    },
    cluster_tweets: function (e) {
        e.preventDefault();
        var self = this;
        var cid = $(e.currentTarget).data("cid");
        var ev = app.eventsCollection.get({cid: $(e.currentTarget).data("eid")});
        console.log("cluster_tweets")
        $.confirm({ //Show tweets
            theme: 'pix-cluster-modal',
            title: 'Cluster' + cid + ' Tweets',
            columnClass: 'col-md-12',
            useBootstrap: true,
            backgroundDismiss: true,
            // content: html,
            content: 'Loading... <div class=" jconfirm-box jconfirm-hilight-shake jconfirm-type-default  jconfirm-type-animated loading" role="dialog"></div>',
            defaultButtons: false,
            onContentReady: function () {

                var jc = this;
                $.post(app.appURL + 'cluster_tweets', {
                    cid: cid,
                    index: app.session.s_index,
                    obj: JSON.stringify(ev)
                }, function (response) {
                    var html = self.get_tweets_html(response, 'static_tweet_box', cid);
                    self.delegateEvents();
                    jc.setContent(html);
                }, 'json');
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
    get_tweets_html: function (response, classes, cid) {
        var html = "";
        var template = _.template($("#tpl-item-tweet").html());
        $.each(response.tweets.results, function (i, tweet) {
            var imgs = "";
            var t_classes = classes;
            if (response.event_tweets) {
                var detected = false;
                $.each(response.event_tweets.results, function (i2, t) {
                    if (t._source.id_str === tweet._source.id_str) {
                        detected = true;
                        return false;
                    }
                });
                if (!detected) {
                    t_classes += ' yellow-tweet';
                }
            }
            if ('extended_entities' in tweet._source) {
                $.each(tweet._source.extended_entities.media, function (i, media) {
                    var ext = "jpg";
                    if (media.media_url.endsWith("png")) {
                        ext = "png";
                    }
                    // imgs += '<a href="http://localhost/TwitterImages/'+app.session.s_index+'/'+tweet._source.id_str+"_"+i+'.'+ext+'" target="_blank"><img style="margin:2px;max-height:150px;width:auto;" src="http://localhost/TwitterImages/'+app.session.s_index+'/'+tweet._source.id_str+"_"+i+'.'+ext+'"></a>'
                    imgs += '<a href="' + app.imagesURL + app.imagesPath + '/' + tweet._source.id_str + "_" + i + '.' + ext + '" target="_blank"><img style="margin:2px;max-height:150px;width:auto;" src="' + app.imagesURL + app.imagesPath + '/' + tweet._source.id_str + "_" + i + '.' + ext + '"></a>'
                });
            }
            var state = tweet._source['session_' + app.session.s_name];
            if (state === "confirmed") {
                state = '<span class="badge badge-success">' + state + '</span>';
            } else if (state === "negative") {
                state = '<span class="badge badge-danger">' + state + '</span>';
            } else {
                state = '<span class="badge badge-secondary">' + state + '</span>';
            }
            html += template({
                tid: tweet._id,
                name: tweet._source.user? "@" + tweet._source.user.name : undefined,
                screen_name: tweet._source.user? tweet._source.user.screen_name : undefined,
                created_at: tweet._source.created_at,
                link: tweet._source.link,
                text: tweet._source.text,
                classes: t_classes,
                images: imgs,
                state: state
            });
        });
        if (response.tweets.scroll_size > 0) {
            html += '<div class="pix-margin-top-10"><a href="#" class="btn btn-lg btn-outline-success full_width scroll_tweets" data-scroll="' + response.tweets.scroll_size + '" data-sid="' + response.tweets.sid + '"> <strong>Load more tweets</strong> </a></div>';
        }
        return html;
    },
    display_tweets: function (response, t0, eid) {
        var html = '';
        html += this.get_tweets_html(response, '');
        var chtml = "";
        var cbtn = "", state_btns = "";
        var i = 0;

        if (app.imagesPath == null || app.imagesPath == undefined) {
            console.log("NO imagesPath");
        }
        app.views.tweets.prototype.showImageClusters(response.clusters, undefined,'#eventsClusters',response.clusters_stats, eid)

        console.log("individual_tweets_result");
        $('.individual_tweets_result:visible:last').html(html);
        $('.loading_text').fadeOut('slow');
        $('.tweets_results').fadeIn('slow');
        if (t0) {
            var t1 = performance.now();
            var time = (t1 - t0) / 1000;
            var roundedString = time.toFixed(2);
            $('.res_num').html(response.tweets.total);
            $('.res_time').html(roundedString);
        }

    },
    tweet_state: function (e) {
        e.preventDefault();
        var tid = $(e.currentTarget).data("tid");
        var val = $(e.currentTarget).data("val");
        var el = $(e.currentTarget).closest('.media-body').find('.t_state');
        //console.log(el);
        $.post(app.appURL + 'mark_tweet', {
            tid: tid,
            index: app.session.s_index,
            session: app.session.s_name,
            val: val
        }, function (response) {
            //console.log(response);
            var state = val;
            if (state === "confirmed") {
                state = '<span class="badge badge-success">' + state + '</span>';
            } else if (state === "negative") {
                state = '<span class="badge badge-danger">' + state + '</span>';
            } else {
                state = '<span class="badge badge-secondary">' + state + '</span>';
            }
            el.html(state);
            app.views.mabed.prototype.getClassificationStats();
        }, 'json');
        return false;
    },
    scroll_tweets: function (e) {
        e.preventDefault();
        var scroll_size = $(e.currentTarget).data("scroll");
        var sid = $(e.currentTarget).data("sid");
        var btn_area = $(e.currentTarget).parent();
        var self = this;
        var data = [];
        data.push({name: "index", value: app.session.s_index});
        data.push({name: "scroll_size", value: scroll_size});
        data.push({name: "sid", value: sid});
        $.post(app.appURL + 'tweets_scroll', data, function (response) {
            var html = self.get_tweets_html(response, '');
            btn_area.replaceWith(html);
        }, 'json').fail(function () {
            $('.loading_text').fadeOut('slow');
            $.confirm({
                title: 'Error',
                boxWidth: '600px',
                theme: 'pix-danger-modal',
                backgroundDismiss: true,
                content: "An error was encountered while connecting to the server, please try again.<br>Error code: tweets__tweets_submit",
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
    cluster_state: function (e) {
        e.preventDefault();
        var state = $(e.currentTarget).data("state");
        var cid = $(e.currentTarget).data("cid");
        var data = [];
        data.push({name: "index", value: app.session.s_index});
        data.push({name: "session", value: "session_" + app.session.s_name});
        data.push({name: "state", value: state});
        data.push({name: "cid", value: cid});
        var jc = $.confirm({
            theme: 'pix-default-modal',
            title: 'Changing tweets state',
            boxWidth: '600px',
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
        $.post(app.appURL + 'mark_cluster', data, function (response) {  // image-based cluster
            //jc.close();
            //data["obj"] = JSON.stringify(app.eventsCollection.get({cid: $(e.currentTarget).data("cid")}));
            app.views.mabed.prototype.getClassificationStats();
            app.views.tweets.prototype.updateImageClusterStatus(e, data);
            jc.close();
        }).fail(function () {
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
    filter_tweets_matching_tab: function (evt) {
        evt.preventDefault();
        console.log("filter_tweets");
        this.filter_tweets(evt, this.currentClusterId, evt.target.getAttribute("tag"));
        $('#event-results-tabs-area li').removeClass('active');
        $(evt.target).parent().addClass('active');
    },
    filter_ngrams_matching_tab: function (evt) {

        evt.preventDefault();
        console.log("filter_ngrams_matching_tab");
        $('.event-ngrams').html("");
        $('#event-ngrams-tabs li').removeClass('active');
        $(evt.target).parent().addClass('active');

        this.load_ngrams(this.lastNgramsEventId);
    },
    filter_tweets: function (e, eid, state) {
        e.preventDefault();
        var eid = (eid != undefined) ? eid : $(e.currentTarget).data("eid"); //c1 c2 c5
        var ev = app.eventsCollection.get({cid: eid}).toJSON();
        var state = (state != undefined) ? state : $(e.currentTarget).data("state");
        var session = 'session_' + app.session.s_name;
        var self = this;
        $('.tweets_results').fadeOut('slow');
        $('.loading_text').fadeIn('slow');
        var t0 = performance.now();
        $.post(app.appURL + 'event_filter_tweets', {
            obj: JSON.stringify(ev),
            index: app.session.s_index,
            state: state,
            session: session
        }, function (response) {
            self.display_tweets(response, t0, eid);
        }, 'json');
        return false;
    }
});
