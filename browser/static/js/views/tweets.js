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
    },
    initialize: function() {
        this.render();
        var handler = _.bind(this.render, this);
        var self = this;
        $(document).on("click","body .tweet_state",function(e){
			self.tweet_state(e);
		});
    },
    render: function(){
        var html = this.template();
        this.$el.html(html);
        this.delegateEvents();
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
                        btnClass: 'btn-cancel',
                    }
                }
            });
          return false;
      }
      $('#tweets_results').fadeOut('slow');
      $('.loading_text').fadeIn('slow');
      var t0 = performance.now();
      var data = $('#tweets_form').serializeArray();
      data.push({name: "index", value: app.session.s_index});
      var self = this;
      $.post(app.appURL+'tweets', data, function(response){
        self.display_tweets(response, t0, data[0].value);
      }, 'json').fail(function() {
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
    cluster_tweets: function(e){
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
    display_tweets: function(response, t0, word){
        var html = '';
        html += '<div class="col-12 pix-padding-top-30 pix-padding-bottom-30">\n' +
            '                    <a class="btn btn-lg btn-success pix-white fly shadow scale btn_filter" data-state="confirmed" href="#" role="button"><strong>Confirmed</strong></a>\n' +
            '                    <a class="btn btn-lg btn-danger pix-white fly shadow scale btn_filter" data-state="negative" href="#" role="button"><strong>Negative</strong></a>\n' +
            '                    <a class="btn btn-lg btn-primary pix-white fly shadow scale btn_filter" data-state="proposed" href="#" role="button"><strong>Proposed</strong></a>\n' +
            '              </div>';
        html += this.get_tweets_html(response, '');
        var chtml = "";
        var cbtn = "", state_btns="";
        if(response.clusters){
            $.each(response.clusters, function(i, cluster){
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
        $('#tweets_result').html(html);
        $('.loading_text').fadeOut('slow');
        $('#tweets_results').fadeIn('slow');
        if(t0){
            var t1 = performance.now();
            var time = (t1 - t0) / 1000;
            var roundedString = time.toFixed(2);
            $('#res_num').html(response.tweets.total);
            $('#res_time').html(roundedString);
        }

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
          }, 'json').fail(function() {
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
        var data = $('#tweets_form').serializeArray();
      data.push({name: "index", value: app.session.s_index});
      data.push({name: "state", value: state});
      data.push({name: "session", value:  'session_'+app.session.s_name});
      var self = this;
      $.post(app.appURL+'tweets_filter', data, function(response){
        self.display_tweets(response, t0, data[0].value);
      }, 'json').fail(function() {
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
    all_tweets_state: function(e){
        e.preventDefault();
        var state = $(e.currentTarget).data("state");
        var data = $('#tweets_form').serializeArray();
        var force = document.getElementById('force_all');

         data.push({name: "index", value: app.session.s_index});
            data.push({name: "session", value: app.session.s_name});
            data.push({name: "state", value: state});

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
                console.log(response);
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
                console.log(response);
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
