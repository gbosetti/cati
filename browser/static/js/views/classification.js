app.views.classification = Backbone.View.extend({
    template: _.template($("#tpl-classify-tweets").html()),
    initialize: function() {
        var handler = _.bind(this.render, this);
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

        $("#remove-stopwords-al").bootstrapToggle();

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

        this.spinner.remove();
        var tweetsHtml = '', ids;
        questions.forEach(question => {
            // var filename = question.filename.replace(/^.*[\\\/]/, ''); // question.filename is a full path also with the file extension
            tweetsHtml = tweetsHtml + ' <div class="card p-3 " id="' + question.data_unlabeled_index + '" data-fullpath="' + question.filename + '"> ' +
                                            '<div class="card-body"> ' +
                                                '<p class="card-text">' + question.text + '</p> ' +
                                                '<p class="card-text"> ' +
                                                    '<i>Confidence</i>: ' + (question.confidence).toFixed(2) + '<br> ' +
                                                    '<i>Predicted</i>: ' + question.pred_label +
                                                '</p> ' +
                                                '<div class=""> ' +
                                                    '<input type="checkbox" data-toggle="toggle" data-on="Confirmed" data-off="Negative" data-onstyle="success" data-offstyle="danger">' +
                                                '</div> ' +
                                            '</div> ' +
                                        '</div>';
        })

        $("#tweet-questions").html(tweetsHtml);

        $(".card .card-body input").each(function() {
            $(this).bootstrapToggle();
            this.style.padding = "right";
        });
    },
    requestTweetsForLearningStage: function(numQuestions){

        $(".card-columns").html('');
        document.querySelector("#tweet-questions").parentElement.appendChild(this.spinner);
        var removeStopwords = document.querySelector("#remove-stopwords-al").checked;

        data = [
            {name: "num_questions", value: numQuestions },
            {name: "remove_stopwords", value: removeStopwords }
        ];

        $.post(app.appURL+'start_learning', data, response => {
            this.loadTweetsForLearningStage(response);
        }, 'json');
    },
    getQuestionsFromUI: function(){

        var questions = [];
        document.querySelectorAll(".card").forEach(question => {
            var label = (question.querySelector("input").checked)? "pos" : "neg"; //The labels in the folders used by the active_learning.py algorythm
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
        data = [{name: "questions", value: JSON.stringify(questions) }]

        $.post(app.appURL+'suggest_classification', data, response => {

            this.generateVisualizationsForValidation(response["positiveTweets"], response["negativeTweets"]);
        }, 'json');
    },
    generateVisualizationsForValidation: function(positiveTweets, negativeTweets){

        var positiveLabels = [];
        positiveTweets.confidences.forEach(conf => { positiveLabels.push("Lorem Ipsum es simplemente el texto de relleno de las imprentas y archivos de texto. Lorem Ipsum ha sido el texto de relleno estándar de las industrias ...")});

        var positiveTweetsTrace = {
            x: positiveTweets.confidences,
            text: positiveLabels,
            boxpoints: 'all',
            type: 'box',
            name: 'Positive'
        };

        var negativeTweetsTrace = {
            x: negativeTweets.confidences,
            text: positiveLabels,
            hoverinfo: 'x+y+text',
            boxpoints: 'all',
            type: 'box',
            name: 'Negative'
        };

        Plotly.newPlot('classification-boxplots', [positiveTweetsTrace, negativeTweetsTrace], {
            xaxis: {
                title: 'Confidence',
                showgrid: true,
                gridcolor: '#dadee2',
                dtick: 0.1,
                zeroline: false
            },
            yaxis: {
                zeroline: false
            },
            showlegend: false,
            margin: {
                l: 100,
                r: 0,
                b: 100,
                t: 0
            }
        });



        document.getElementById('classification-boxplots').on('plotly_hover', function(data){
            if(data.points && data.points.length > 0){

                console.log("Point", data.points[0]);

                var hoverInfo = document.getElementById('hoverinfo');
                console.log(hoverInfo);
            }
        });

//        var myPlot = document.getElementById('classification-boxplots');
//        myPlot.on('plotly_click', function(data){
//            if(data.points && data.points.length > 0){
//                var yAxis = data.event.clientY * data.points[0].x / data.event.clientX;
//                var annotation = { text: "TEXT", x: data.points[0].x, y:yAxis };
//                annotations = []; // self.layout.annotations || [];
//                annotations.push(annotation);
//                Plotly.relayout('classification-boxplots',{annotations: annotations})
//            }
//        });
    }
});