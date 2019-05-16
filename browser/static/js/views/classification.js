app.views.classification = Backbone.View.extend({
    template: _.template($("#tpl-classify-tweets").html()),
    //lsampleQueriesTemplate: _.template($("#tpl-classify-tweets").html()), //This way we have the template without any post change
    initialize: function() {
        var handler = _.bind(this.render, this);

        app.views.mabed.prototype.setSessionTopBar();

        String.prototype.chunk = function(size) {
            return [].concat.apply([],
                this.split('').map(function(x,i){ return i%size ? [] : this.slice(i,i+size) }, this)
            )
        }

    },
    render: function(){

        var html = this.template();
        this.$el.html(html);
        this.delegateEvents();
        this.initializeSpinner();
        this.isProcessStarted=false;

        //var tplSamplingStage = '<div class="carousel-item validation-stage">' + $(".sampling-stage").html() + "</div>";
        /*this._tplSamplingStage: $(".sampling-stage").html();
        this._tplValidationStage: $(".validation-stage").html();*/
        $( "#carouselExampleIndicators" ).on( "click", ".keep-training-btn", function() {
            //console.log("\n\nnew template", tplSamplingStage);
            //$('.carousel-item').removeClass('active');
            //$('.carousel-inner').append(tplSamplingStage);
            //$('.sampling-stage').addClass('active');
            $('.carousel').carousel(1);
        });

        this.initializeSamplingStrategyTab();

        document.querySelector("#start-automatic-learning").addEventListener("click", () => {
            this.numSampleQueries = document.querySelector("#num-tweet-questions").value;
        });

        document.querySelector(".to-al-validation-stage").addEventListener("click", () => {
            this.lastLoadedQuestions = this.getQuestionsFromUI();
        });

        $('#carouselExampleIndicators').on('slide.bs.carousel', (evt) => {

            $(".tweet-questions").html("");
            $("#classif-graph-area").html("");
        });

        $('#carouselExampleIndicators').on('slid.bs.carousel', (evt) => {

            if (evt.to == 1){
                this.loadSamplingStage().then(()=>{
                    this.spinner.remove();
                });
            }
            else if (evt.to == 2){
                this.loadValidationStage().then(()=>{
                    this.spinner.remove();
                });
            }
        });

        //$("#remove-stopwords-al").bootstrapToggle();
        app.views.mabed.prototype.getClassificationStats();
        //app.views.mabed.prototype.setSessionTopBar();

        return this;
    },
    loadSamplingStage: function(){

        $(".tweet-questions")[0].parentElement.appendChild(this.spinner);

        var data = [
            {name: "index", value: app.session.s_index},
            {name: "session", value: "session_" + app.session.s_name},
            {name: "gt_session", value: "session_lyon2017_test_gt"}, //TODO
            {name: "num_questions", value: this.numSampleQueries },  // do the TODOs like in this way
            {name: "max_samples_to_sort", value:500}, //TODO
            {name: "text_field", value:"2grams"}, //TODO
            {name: "is_field_array", value:false}, //TODO
            {name: "debug_limit", value:true}, //TODO
            {name: "download_data", value:false}
        ];

        if(this.isProcessStarted){
            console.log("Re-training");
            return this.trainModel(data);
        }
        else{
            console.log("First training");
            return new Promise((resolve, reject)=>{
                this.initLearningProcess(data).then(()=>{
                    this.isProcessStarted = true;
                    this.trainModel(data).then(()=>{
                        resolve();
                    });
                });
            });
        }
    },
    loadValidationStage: function(){

        $("#classif-graph-area").append(this.spinner);
        return this.suggestClassification();
    },
    initializeSamplingStrategyTab: function(){

        $( '#classification-strategies-tabs .nav-item a' ).on( 'click', (elem) => {
            $( '#classification-strategies-tabs' ).find( 'li.active' ).removeClass( 'active' );
            $( elem ).parent( 'li' ).addClass( 'active' );
            $('.popover-dismiss').popover({ html: true});
            this.isProcessStarted=false; //Restart the process
            $(".carousel").carousel(0); //Restart the carousel

            setTimeout(()=>{
                var loadingMethod = $('.nav-link.show').attr("on-pane-load");
                if(loadingMethod)
                    this[loadingMethod]();
            }, 1000);
        });
    },
    initializeExtendedUncertaintySampling: function(){

        $("#configs").html("");
        var configs = [[0.0, 0.0, 1.0], [0.0, 0.2, 0.8], [0.0, 0.4, 0.6], [0.0, 0.6, 0.4], [0.0, 0.8, 0.2], [0.0, 1.0, 0.0], [0.2, 0.0, 0.8], [0.2, 0.2, 0.6], [0.2, 0.4, 0.4], [0.2, 0.6, 0.2], [0.2, 0.8, 0.0], [0.4, 0.0, 0.6], [0.4, 0.2, 0.4], [0.4, 0.4, 0.2], [0.4, 0.6, 0.0], [0.6, 0.0, 0.4], [0.6, 0.2, 0.2], [0.6, 0.4, 0.0], [0.8, 0.0, 0.2], [0.8, 0.2, 0.0], [1.0, 0.0, 0.0]];
        configs.forEach(cfg => {
            var hyp = parseFloat(cfg[0]) * 100;
            var dup = parseFloat(cfg[1]) * 100;
            var bgr = parseFloat(cfg[2]) * 100;

            console.log(cfg);
            $("#configs").append("<option value='"+ cfg.toString() +"'>hyp(" + hyp + ") dup(" + dup + ") bgr(" + bgr + ")</option>");
        });
    },
    initializeSpinner: function(){

        // <div class="card-columns" id="tweet-questions" style="width: 120px; margin: 0 auto; min-height: 200px; padding-top: 3em;">
        var container = document.createElement("div");
            container.className = "card-columns";
            container.style.width = "120px";
            container.style.margin = "0 auto";
            container.style["min-height"] = "200px";
            container.style["padding-top"] = "3em";

        var spinner = document.createElement("div");
            spinner.className = "loader"; //new Spinner();
            //spinner.style.float = "right";

        container.appendChild(spinner);
        this.spinner = container;
    },
    loadTweetsForLearningStage: function(questions){

        var tweetsHtml = '', ids;

        this.getRelatedTweetsToQueries(questions).then(question_rel_tweets => {

            $(".tweet-questions").html(""); //Make sure everything is clear before loading the new questions
            questions.forEach(question => {

                question.bigrams = question.text;
                question.text = question_rel_tweets.filter(tweet => tweet._source.id_str == question.str_id)[0]["_source"]["text"];
                question.imageSrc = app.imagesURL + app.imagesPath +'/'+ question.str_id + "_0.jpg";

                // var filename = question.filename.replace(/^.*[\\\/]/, ''); // question.filename is a full path also with the file extension
                tweetsHtml += ' <div class="card p-3 " id="' + question.data_unlabeled_index + '" data-fullpath="' + question.filename + '"> ' +
                                                '<img class="card-img-top" src="' + question.imageSrc + '" alt=""> ' +
                                                '<div class="card-body"> ' +
                                                    '<p class="card-text">' + question.text + '</p> ' +
                                                    '<p class="card-text"> ' +
                                                        '<i>Confidence</i>: ' + (question.confidence).toFixed(2) + '<br> ' +
                                                        '<i>Predicted</i>: ' + question.pred_label +
                                                    '</p> ' +
                                                    '<div class=""> ' +
                                                        '<input type="checkbox" data-toggle="toggle" data-on="Confirmed" data-off="Negative" data-onstyle="success" data-offstyle="danger" ';

                                                        if(question.pred_label == "confirmed"){
                                                            tweetsHtml += 'checked';
                                                        }

                                                        tweetsHtml += '>' +
                                                    '</div> ' +
                                                '</div> ' +
                                            '</div>';
            })

            $(".tweet-questions").html(tweetsHtml);

            $(".card .card-body input").each(function() {
                $(this).bootstrapToggle();
                this.style.padding = "right";
            });
        });
    },
    getRelatedTweetsToQueries: function(questions){

        return new Promise(function(resolve, reject) {
            questions_ids = "";
            questions.forEach(question => {
                questions_ids += question.str_id + " or ";
            });
            questions_ids = questions_ids.substring(0, questions_ids.length-3);

            data = [
                {name: "index", value: app.session.s_index},
                {name: "id_strs", value: questions_ids}
            ];

            $.post(app.appURL+'get_tweets_by_str_ids', data, response => {
                resolve(response)
            }, 'json');
        });
    },
    initLearningProcess: function(data){
        return new Promise((resolve, reject) => {
            $.post(app.appURL+'download_al_init_data', data, response => {
                this.last_al_scores = response.scores;
                this.loadTweetsForLearningStage(response.questions);
                resolve();
            }, 'json');
        });
    },
    trainModel: function(data){

        return new Promise((resolve, reject) => {

            $.post(app.appURL+'train_model', data, response => {
                this.last_al_scores = response.scores;
                this.loadTweetsForLearningStage(response.questions);
                resolve();
            }, 'json');
        });
    },
    getQuestionsFromUI: function(){

        var questions = [];
        document.querySelectorAll(".card").forEach(question => {
            var label = (question.querySelector("input").checked)? "confirmed" : "negative"; //The labels in the folders used by the active_learning.py algorythm
            var labeled_question = {};
                labeled_question["id"] = question.id;
                labeled_question["label"] = label;
                labeled_question["filename"] = question.getAttribute("data-fullpath");
            questions.push(labeled_question);
        });
        return questions;
    },
    renderALClassificationArea: function(){

        $("#classif-graph-area").html("");
        $("#classif-graph-area").html(`<div style="padding:5px">
          <div class="row">
            <!-- HEADERS -->
            <div class="row col">
              <div id="cloud_header_q1" class="col-2 d-flex justify-content-center">
                <div class="align-self-center p-2">
                  Confidence
                </div>
              </div>
              <div id="cloud_header_q1" class="col-5 d-flex justify-content-center">
                <div class="align-self-center p-2">
                  Bigrams on positive documents
                </div>
              </div>
              <div id="cloud_header_q2" class="col-5 d-flex justify-content-center">
                <div class="align-self-center p-2">
                  Bigrams on negative documents
                </div>
              </div>
            </div>
          </div>

          <div class="row">
            <!-- Q1 Q2 -->
            <div class="row col">
              <div id="cloud_slider" class="col-2 d-flex justify-content-center">
                <div id="content" >
                  <div id="pips-range-vertical" class="slider-range"></div>
                </div>
              </div>
              <div id="cloud_q1" class="col-5 border tag-cloud"></div>
              <div id="cloud_q2" class="col-5 border tag-cloud"></div>
            </div>
          </div>

          <div class="row">
            <div class="row col-12">
                <form class="static_box pix-padding-20 white-bg bigrams-controls">
                  <div class="form-row">
                    <div class="col-3">
                      <label>Max bigrams to show</label>
                      <div class="input-group mb-3">
                        <input name="top-bubbles-to-display" type="number" class="form-control top-bubbles-to-display" value="20" min="1">
                        <div class="input-group-append">
                          <button class="btn btn-default" type="submit"><i class="fa fa-refresh"></i></button>
                        </div>
                      </div>
                     </div>
                  </div>

                </form>
              </div>
          </div>
        </div>`);
    },
    suggestClassification: function(){

        return new Promise((resolve, reject)=>{
            setTimeout(()=>{ //Temporary to check the UI behaviour

                this.renderALClassificationArea();
                data = [
                    {name: "index", value: app.session.s_index},
                    {name: "session", value: "session_" + app.session.s_name},
                    {name: "questions", value: JSON.stringify(this.lastLoadedQuestions) },
                    {name: "scores", value: JSON.stringify(this.last_al_scores)},
                    {name: "results_size", value:"20"}
                ];

                $.post(app.appURL+'suggest_classification', data, response => {
                    this.drawNgrams("#cloud_q1", response.pos, "confirmed");
                    this.drawNgrams("#cloud_q2", response.neg, "negative");
                    this.drawQuadrantsSlider('pips-range-vertical');
                    resolve();
                }, 'json');

            }, 5000);
        });
    },
    drawQuadrantsSlider: function(selector){
         noUiSlider.create(document.getElementById(selector), {
          start: [0.2, 0.5],
          connect: true,
          direction: 'rtl',  // ltr or rtl
          orientation: 'vertical',
          tooltips: true,
          range: {
            'min': 0,
            'max': 1
          },
          pips: { // Show a scale with the slider
            mode: 'steps',
            stepped: false,
            density: 4
          }
       })
    },
    fit_to_max: function(collection, max){

        var sizes = collection.map(elem => { return elem.size });
        var max_in_coll = Math.max(...sizes);
        var min_in_coll = Math.min(...sizes);

        collection.forEach(elem => {

            elem.size = ((elem.size - min_in_coll) / (max_in_coll - min_in_coll)) * max;
        });

        return collection;
    },
    formatQuadrantResults: function(res){

        //return res.map(res => { return {"text": (res.key.length>10)? res.key.substring(0,10) : res.key , "size": res.doc_count }})

        var mapped = res.map(res => { return {"text": res.key , "size": res.doc_count }});
        return this.fit_to_max(mapped, 35);
    },
    generateVisualizationsForValidation: function(positiveTweets, negativeTweets){

        $("#classif-graph-area").html("");
        this.drawQuadrants(positiveTweets, negativeTweets);
        this.drawBoxplot(positiveTweets, negativeTweets);
        this.drawPiechart(positiveTweets, negativeTweets);
        var divHeight = 350;
        //this.drawTagCloud("Most frequent n-grams for <b>positive</b>-labeled tweets", positiveTweets.texts, "positive-labeled-tweets-cloud", divHeight, "positiveTweets");
        //this.drawTagCloud("Most frequent n-grams for <b>negative</b>-labeled tweets", negativeTweets.texts, "negative-labeled-tweets-cloud", divHeight, "negativeTweets");

        // Store them for user manipulation
        this.positiveTweets = positiveTweets;
        this.negativeTweets = negativeTweets;
    },
    drawNgrams: function(containerSelector, ngrams, category){

        //console.log("drawNgrams",containerSelector, app.session.s_index, app.session.s_name);
        //var event = app.eventsCollection.get({cid: this.lastNgramsEventId}).toJSON();

        var widget = new BubbleWidget(containerSelector, app.session.s_index, 'session_'+app.session.s_name, 500, "proposed"); //Proposed since the data being classified is the unlabeled, and it doesn't change in Elasticsearch until the end of the process
        var formatted_ngrams;

        if(category == "confirmed"){

            formatted_ngrams = ngrams.map(ngram => {  //// [ bigram[0], [bigram_confirmed, bigram_negative, bigram_unlabeled] ]
                return [
                    ngram.key.split(/-+/).join(" "), [
                        this.filterElemByKey("proposed", ngram.status.buckets), [], []
                    ]
                ]
            });
        } else{

            formatted_ngrams = ngrams.map(ngram => {  //// [ bigram[0], [bigram_confirmed, bigram_negative, bigram_unlabeled] ]
                return [
                    ngram.key.split(/-+/).join(" "), [
                        [], this.filterElemByKey("proposed", ngram.status.buckets), []
                    ]
                ]
            });
        }



        widget.render(formatted_ngrams);

//        console.log("000");
//        $(containerSelector).html("");
//        app.views.tweets.prototype.renderBigramsGrid(containerSelector, 300, false, "col-12");
//        console.log("001");
//        app.views.tweets.prototype.updateBigramsControls(ngrams, this.ngrams);
//        console.log("002");
//
//        var onBubbleClick = (label, evt) => {
//
//            var ngram = label.split(" ").join("-");
//            var ngramsToGenerate = this.ngrams.formData.filter(item => {
//                return item.name == "n-grams-to-generate"
//            })[0];
//            ngramsToGenerate = ngramsToGenerate != undefined ? ngramsToGenerate.value : 2;
//            app.views.tweets.prototype.showNgramTweets(this.ngrams, this, ngramsToGenerate, label, ngram, "#event-ngrams-tabs li.active a", 'search_event_bigrams_related_tweets');
//        };
//
//        app.views.tweets.prototype.renderBigramsChart(onBubbleClick, this.ngrams, ".bigrams-graph-area", ngrams, 600);

    },
    filterElemByKey: function(key, collection){
        var res = collection.filter(item => {return item.key == key});
        return (res && res[0] && res[0].doc_count)? res[0]["doc_count"] : 0;
    },
   /*
   drawD3TagCloud: function(data, selector, width, height){

        $(selector).html("");
        $(selector).css("width", width);
        $(selector).css("height", height);

		var fill = d3.scale.category20();
        d3.layout.cloud()
            .size([width, height])
            .words(data)
            .rotate(0)
            //.padding(3)
            .font("Impact")
            .fontSize(function(d) {
                return d.size;
            })
            .on("end", drawCloud)
            .start();

        // apply D3.js drawing API
        function drawCloud(words) {
            d3.select(selector).append("svg")
                .attr("width", width)
                .attr("height", height)
                .append("g")
                .attr("transform", "translate(" + ~~(width / 2) + "," + ~~(height / 2) + ")")
                .selectAll("text")
                .data(words)
                .enter().append("text")
                .style("font-size", function(d) {
                    return d.size + "px";
                })
                .style("-webkit-touch-callout", "none")
                .style("-webkit-user-select", "none")
                .style("-khtml-user-select", "none")
                .style("-moz-user-select", "none")
                .style("-ms-user-select", "none")
                .style("user-select", "none")
                .style("cursor", "default")
                .style("font-family", "Impact")
                .style("fill", function(d, i) {
                    return fill(i);
                })
                .attr("text-anchor", "middle")
                .attr("transform", function(d) {
                    return "translate(" + [d.x, d.y] + ")";
                    //return "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")";
                })
                .text(function(d) {
                    return d.text;
                });
        };

        var svg = document.querySelector(selector).getElementsByTagName("svg")[0];
        var bbox = svg.getBBox();
        var viewBox = [bbox.x, bbox.y, bbox.width, bbox.height].join(" ");
        svg.setAttribute("viewBox", viewBox);
    },
    drawTagCloud: function(title, tweetsTexts, divId, divHeight, tweetsTextsVarName){

        $("#classif-graph-area").append(
            '<h5 class="mt-5" align="center">' + title + '</h5>' +
            '<div id="' + divId + '-container" class="classif-visualization"> ' +
                '<div id="' + divId + '" style="width: 100%; height: ' + divHeight + 'px; background: white;"></div>' +
            '</div>'
        );

        // Default values
        nGramsToGenerate = 2;
        topNgramsToRetrieve = 25;
        removeStopwords = true;
        stemWords = true;

        console.log("Retrieving for ", tweetsTextsVarName);
        this.retrieveNGrams(tweetsTexts, nGramsToGenerate, topNgramsToRetrieve, removeStopwords, stemWords).then(ngrams => {

            console.log("ngrams for ", tweetsTextsVarName, ngrams);

            this.renderTagCloud(ngrams, divId, divHeight, tweetsTextsVarName, {
                "nGramsToGenerate": nGramsToGenerate,
                "topNgramsToRetrieve": topNgramsToRetrieve,
                "removeStopwords": removeStopwords,
                "stemWords": stemWords });
        });
    },
    */
    retrieveNGrams: function(tweetTexts, nGramsToGenerate, topNgramsToRetrieve, removeStopwords, stemWords){

        return new Promise(function(resolve, reject) {

            var data = [
                {name: "top_ngrams_to_retrieve", value: topNgramsToRetrieve },
                {name: "tweet_texts", value: tweetTexts },
                {name: "length", value: nGramsToGenerate },
                {name: "remove_stopwords", value: removeStopwords },
                {name: "stemming", value: stemWords }
            ];
            $.post(app.appURL+'most_frequent_n_grams', data, ngrams => {
                resolve(ngrams);
            }, 'json');
        });
    },
    renderTagCloud: function(ngrams, divId, height, tweetsTextsVarName, defaultConfig){

        var skillsToDraw = ngrams.map(ngram => { // { text: 'javascript', size: 1 }
            var text = ngram[0][0] + "-" + ngram[0][1];
            var size = ngram[1];
            return { "text": text, "size": size };
        });

        // Use the layout script to calculate the placement, rotation and size of each word:
        var width = $("#positive-labeled-tweets-cloud").width();
        var fill = d3.scale.category20();
        var angle = 15;

        d3.layout.cloud()
            .size([width, height])
            .words(skillsToDraw)
            .rotate(function() {
                return ~~(Math.random() * 5) * (Math.floor(Math.random() * angle) + -angle); // Originally return ~~(Math.random() * 2) * 90;
            })
            .font("Impact")
            .fontSize(function(d) { return d.size; })
            .on("end", function(words) {

                d3.select("#" + divId).append("svg")
                    .attr("width", width)
                    .attr("height", height)
                    .append("g")
                    .attr("transform", "translate(" + ~~(width / 2) + "," + ~~(height / 2) + ")")
                    .selectAll("text")
                    .data(words)
                    .enter().append("text")
                    .style("font-size", function(d) {
                        return d.size + "px";
                    })
                    .style("-webkit-touch-callout", "none")
                    .style("-webkit-user-select", "none")
                    .style("-khtml-user-select", "none")
                    .style("-moz-user-select", "none")
                    .style("-ms-user-select", "none")
                    .style("user-select", "none")
                    .style("cursor", "default")
                    .style("font-family", "Impact")
                    .style("fill", function(d, i) {
                        return fill(i);
                    })
                    .attr("text-anchor", "middle")
                    .attr("transform", function(d) {
                        return "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")";
                    })
                    .text(function(d) {
                        return d.text;
                    });
            })
            .start();

            // set the viewbox to content bounding box (zooming in on the content, effectively trimming whitespace)
            var svg = document.querySelector("#" + divId).querySelector("svg");
            var bbox = svg.getBBox();
            var viewBox = [bbox.x, bbox.y, bbox.width, bbox.height].join(" ");
            svg.setAttribute("viewBox", viewBox);

        this.drawTagcloudControls(divId, tweetsTextsVarName, defaultConfig);
    },
    drawTagcloudControls: function(divId, tweetsTextsVarName, defaultConfig){

        removeStopwords = (defaultConfig.removeStopwords)? "checked" : "";
        stemWords = (defaultConfig.stemWords)? "checked" : "";

        $("#" + divId).parent().append(`
            <div class="col-12 col-sm-12">
                <div id="${divId}-form" class="static_box pix-padding-20 white-bg">
                    <div class="mt-4 form-row">
                        <div class="col-md-6 col-sm-6 h_field">
                            <label for="n-grams-to-generate">N-grams to generate</label>
                            <input id="n-grams-to-generate" name="top_events" type="number" class="form-control" placeholder="Default to 2" value="${defaultConfig.nGramsToGenerate}">
                        </div>
                        <div class="col-md-6 col-sm-6 h_field">
                            <label for="top-n-grams-to-display">Top-ngrams to display</label>
                            <input id="top-n-grams-to-display" name="min_absolute_frequency" type="text" class="form-control" placeholder="0 = all" value="${defaultConfig.topNgramsToRetrieve}">
                        </div>
                        <div class="col-md-6 col-sm-6 h_field">
                            <label for="remove-stopwords">Remove stopwords</label>
                            <div class="">
                                <input id="remove-stopwords" type="checkbox" data-toggle="toggle" data-on="Confirmed" data-off="Negative" data-onstyle="success" data-offstyle="danger" ${removeStopwords}>
                            </div>
                        </div>
                        <div class="col-md-6 col-sm-6 h_field">
                            <label for="stem-words">Stem words</label>
                            <div class="">
                                <input id="stem-words" type="checkbox" data-toggle="toggle" data-on="Confirmed" data-off="Negative" data-onstyle="success" data-offstyle="danger" ${stemWords}>
                            </div>
                        </div>
                    </div>
                    <div class="mt-4 form-row">
                        <button id="${divId}-regenerate-tag-cloud" dataset="${tweetsTextsVarName}" class="btn btn-lg btn-flat btn-success" style="width:100%"><strong>Apply</strong></button>
                    </div>
                </div>
            </div>`
        );
        $("#" + divId + "-form input[type=checkbox]").each(function() {
            $(this).bootstrapToggle();
        });

        $("#" + divId + "-regenerate-tag-cloud").on("click", ev => {
            this.updateTagCloudView(ev.target);
        })
    },
    updateTagCloudView: function(btn){

        var dataset = $(btn).attr("dataset");
        var tweetTexts = this[dataset].texts;
        var targetFormId = $(btn).parent().parent().attr("id");
        var nGramsToGenerate = $("#" + targetFormId + " #n-grams-to-generate").val();
        var topNgramsToRetrieve = $("#" + targetFormId + " #top-n-grams-to-display").val();
        var removeStopwords = false; //$("#" + targetFormId + " #remove-stopwords").prop("checked");
        var stemWords = $("#" + targetFormId + " #stem-words").prop("checked");
        var graphArea = $("#" + targetFormId).parent().parent();
        var graphHeight = graphArea.children().eq(0).height();
        var graphId = graphArea.attr("id").replace('-container','');
        graphArea.html('');
        graphArea.html('<div id="' + graphId + '" style="width: 100%; height: ' + graphHeight + 'px; background: white;"></div>');

        this.retrieveNGrams(tweetTexts, nGramsToGenerate, topNgramsToRetrieve, removeStopwords, stemWords).then(ngrams => {
            this.renderTagCloud(ngrams, graphId, graphHeight, dataset, {
            "nGramsToGenerate": nGramsToGenerate,
            "topNgramsToRetrieve": topNgramsToRetrieve,
            "removeStopwords": removeStopwords,
            "stemWords": stemWords });
        });
    },
    drawBoxplot: function(positiveTweets, negativeTweets){

        $("#classif-graph-area").append(
            '<div> ' +
                '<h5 class="mt-5" align="center">Confidence of the predicted tweets\' labels</h5>' +
                '<div id="classification-boxplots" class="classif-visualization graph js-plotly-plot" style="height: 500px; width: 100%; min-width: 500px; max-height: 500px;"></div>' +
            '</div>'
         );

        var positiveLabels = positiveTweets.texts.map(text => {
            return text.chunk(45).join("<br>");
        });
        var negativeLabels = negativeTweets.texts.map(text => {
            return text.chunk(45).join("<br>");
        });

        var positiveTweetsTrace = {
            y: positiveTweets.confidences,
            text: positiveLabels,
            hoverinfo: 'y+text',
            boxpoints: 'all',
            type: 'box',
            name: 'Positive'
        };

        var negativeTweetsTrace = {
            y: negativeTweets.confidences,
            text: negativeLabels,
            hoverinfo: 'y+text',
            boxpoints: 'all',
            type: 'box',
            name: 'Negative'
        };

        Plotly.newPlot('classification-boxplots', [positiveTweetsTrace, negativeTweetsTrace], {
            yaxis: {
                title: 'Confidence',
                showgrid: true,
                gridcolor: '#dadee2',
                dtick: 0.1,
                zeroline: false
            },
            xaxis: {
                zeroline: false
            },
            showlegend: false,
            margin: {
                l: 100,
                r: 0,
                b: 50,
                t: 50
            }
        });
    },
    drawPiechart: function(positiveTweets, negativeTweets){

        $("#classif-graph-area").append(
            '<h5 class="mt-5" align="center">Tweets by predicted label</h5>' +
            '<div id="classification-piechart" class="classif-visualization graph js-plotly-plot" style="height: 400px; width: 100%; min-width: 500px;"></div>'
         );

        var data = [{
            values: [positiveTweets.confidences.length, negativeTweets.confidences.length],
            labels: ['Positive', 'Negative'],
            type: 'pie'
        }];

        Plotly.newPlot('classification-piechart', data, {});
    }
});