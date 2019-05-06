app.views.classification = Backbone.View.extend({
    template: _.template($("#tpl-classify-tweets").html()),
    initialize: function() {
        var handler = _.bind(this.render, this);

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

        $( '#classification-strategies-tabs .nav-item a' ).on( 'click', function () {
            $( '#classification-strategies-tabs' ).find( 'li.active' ).removeClass( 'active' );
            $( this ).parent( 'li' ).addClass( 'active' );
        });

        document.querySelector("#start-automatic-learning").addEventListener("click", () => {

            var numQuestions = document.querySelector("#num-tweet-questions").value;
            this.requestTweetsForLearningStage(numQuestions);
        });

        /*document.querySelector("#to-learning-stage").addEventListener("click", () => {
            document.querySelector("#tweet-questions").parentElement.appendChild(this.spinner);
        });*/

        document.querySelector("#to-al-validation-stage").addEventListener("click", () => {
            this.suggestClassification();
        });

        //$("#remove-stopwords-al").bootstrapToggle();
        app.views.mabed.prototype.getClassificationStats();
        //app.views.mabed.prototype.setSessionTopBar();

        return this;
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

        console.log(questions);
        this.spinner.remove();
        var tweetsHtml = '', ids;

        this.getRelatedTweetsToQueries(questions).then(question_rel_tweets => {

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

            $("#tweet-questions").html(tweetsHtml);

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
    requestTweetsForLearningStage: function(numQuestions){

        $(".card-columns").html('');
        document.querySelector("#tweet-questions").parentElement.appendChild(this.spinner);
        var removeStopwords = false; //document.querySelector("#remove-stopwords-al").checked;

        data = [
            {name: "index", value: app.session.s_index},
            {name: "session", value: "session_" + app.session.s_name},
            {name: "gt_session", value: "session_lyon2017_test_gt"}, //TODO
            {name: "num_questions", value: numQuestions },
            {name: "remove_stopwords", value: removeStopwords },
            {name: "max_samples_to_sort", value:500}, //TODO
            {name: "text_field", value:"2grams"}, //TODO
            {name: "is_field_array", value:false}, //TODO
            {name: "debug_limit", value:true}
        ];

        $.post(app.appURL+'start_learning', data, response => {
            console.log(response);
            this.last_al_scores = response.scores;
            this.loadTweetsForLearningStage(response.questions);
        }, 'json');
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
    suggestClassification: function(){

        var questions = this.getQuestionsFromUI();
        data = [
            {name: "index", value: app.session.s_index},
            {name: "session", value: "session_" + app.session.s_name},
            {name: "questions", value: JSON.stringify(questions) },
            {name: "scores", value: JSON.stringify(this.last_al_scores)},
            {name: "results_size", value:"7"}
        ];

        $.post(app.appURL+'suggest_classification', data, response => {
            console.log("RESPONSE", response);
            this.drawQuadrants( this.formatQuadrantResults(response.high.pos),
                                this.formatQuadrantResults(response.high.neg),
                                this.formatQuadrantResults(response.low.pos),
                                this.formatQuadrantResults(response.low.neg));
            //this.generateVisualizationsForValidation(response["positiveTweets"], response["negativeTweets"]);
        }, 'json');
    },
    formatQuadrantResults: function(res){

        return res.map(res => { return {"text": res.key , "size": res.doc_count }})
    },
    generateVisualizationsForValidation: function(positiveTweets, negativeTweets){

        $("#classif-graph-area").html("");
        this.drawQuadrants(positiveTweets, negativeTweets);
        this.drawBoxplot(positiveTweets, negativeTweets);
        this.drawPiechart(positiveTweets, negativeTweets);
        var divHeight = 350;
        this.drawTagCloud("Most frequent n-grams for <b>positive</b>-labeled tweets", positiveTweets.texts, "positive-labeled-tweets-cloud", divHeight, "positiveTweets");
        this.drawTagCloud("Most frequent n-grams for <b>negative</b>-labeled tweets", negativeTweets.texts, "negative-labeled-tweets-cloud", divHeight, "negativeTweets");

        // Store them for user manipulation
        this.positiveTweets = positiveTweets;
        this.negativeTweets = negativeTweets;
    },
    drawQuadrants: function(highPos, highNeg, lowPos, lowNeg){

        this.drawD3TagCloud(highPos, "#cloud_q1", 400, 250);
        this.drawD3TagCloud(highNeg, "#cloud_q2", 400, 250);
        this.drawD3TagCloud(lowPos, "#cloud_q3", 400, 250);
        this.drawD3TagCloud(lowNeg, "#cloud_q4", 400, 250);
    },
    drawD3TagCloud: function(data, selector, width, height){

        $(selector).html("");

		var fill = d3.scale.category20();
        d3.layout.cloud()
            .size([width, height])
            .words(data)
            .rotate(function() {
                return ~~(Math.random() * 2) * 90;
            })
            .font("Impact")
            .fontSize(function(d) {
                return d.size;
            })
            .on("end", drawSkillCloud)
            .start();

        // apply D3.js drawing API
        function drawSkillCloud(words) {
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
                    return "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")";
                })
                .text(function(d) {
                    return d.text;
                });
        }

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