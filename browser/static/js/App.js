// var app_url = "http://localhost:5000/";
app_url = (app_url.lastIndexOf("/") == app_url.length - 1) ? app_url : app_url + "/";

var app = (function () {

    var api = {
        views: {},
        models: {},
        collections: {},
        content: null,
        router: null,
        session_id: null,
        session: null,
        eventsCollection: null,
        imagesPath: null,
        appURL: app_url,
        init: function () {
            this.content = $("#content");
            this.eventsCollection = new app.collections.events();
            this.imagesURL = app_url + 'static/images/';

            if (localStorage.getItem('session_id') !== null) {
                var sessionString = localStorage.getItem('session');
                this.session = JSON.parse(sessionString);
                this.session_id = localStorage.getItem('session_id');
                if (this.session.events) {
                    var collection = JSON.parse(this.session.events);
                    this.eventsCollection.add_json_events(collection);
                }
            }
            if (localStorage.getItem('image_path') != undefined || localStorage.getItem('image_path') != null) {
                this.imagesPath = localStorage.getItem('image_path');

            }
            /*else{
                var self = this;
                console.log('get_image_folder');
                $.post(app.appURL+'get_image_folder', [{name:"index", value:app.session.s_index}],  function(folderName){
                    console.log('folderName: ', folderName);
                    self.imagesPath = folderName;
                    localStorage.setItem('image_path', folderName);
                });
            }*/

            Backbone.history.start();
            return this;
        },
        changeContent: function (el) {
            this.content.empty().append(el);
            return this;
        },
        title: function (str) {
            $("#title").text(str);
            $("title").text(str + " | CATI");
            return this;
        }
    };

    var ViewsFactory = {
        home: function () {
            if (!this.homeView) {
                this.homeView = new api.views.home();
            }
            return this.homeView;
        },
        classification: function () {

            if (!this.classificationView) {
                this.classificationView = new api.views.classification();
            }
            return this.classificationView;
        },
        settings: function () {
            if (!this.settingsView) {
                this.settingsView = new api.views.settings();
            }
            return this.settingsView;
        },
        tweets: function () {
            if (!this.tweetsView) {
                this.tweetsView = new api.views.tweets();
            }
            return this.tweetsView;
        },
        mabed: function () {  // "Detect events using MABED" tab
            if (!this.mabedView) {
                this.mabedView = new api.views.mabed({
                    model: api.eventsCollection
                });
            }
            return this.mabedView;
        },
        beta: function () {
            if (!this.betaView) {
                this.betaView = new api.views.beta({
                    model: api.eventsCollection
                });
            }
            return this.betaView;
        },
        beta2: function () {
            if (!this.beta2View) {
                this.beta2View = new api.views.beta2({
                    model: api.eventsCollection
                });
            }
            return this.beta2View;
        },
        client: function () {
            if (!this.clientView) {
                this.clientView = new api.views.client({
                    model: api.clientCollection
                }).on("saved, submit", function (e) {
                    e.preventDefault();
                    api.router.navigate("client", {trigger: false});
                });
            }
            return this.clientView;
        },
        review: function () {
            if (!this.reviewView) {
                this.reviewView = new api.views.review({
                    model: api.clientCollection
                });
            }
            return this.reviewView;
        }
    };

    var Router = Backbone.Router.extend({
        routes: {
            "results": "results",
            "settings": "settings",
            "tweets": "tweets",
            "classification": "classification",
            "mabed": "mabed",
            "review": "review",
            "beta": "beta",
            "beta2": "beta2",
            "": "home"
        },
        home: function () {
            var view = ViewsFactory.home();
            $('#mabed-nav .nav-item').removeClass('active');
            $('#nav-home').addClass('active');
            api
                .title("Homepage")
                .changeContent(view.$el);
            view.render();
            $('html,body').animate({scrollTop: 0}, 300);

        },
        classification: function () {

            var view = ViewsFactory.classification();
            $('#mabed-nav .nav-item').removeClass('active');
            $('#nav-classification').addClass('active');

            api.title("Classification").changeContent(view.$el);
            view.render();
        },
        settings: function () {
            var view = ViewsFactory.settings();
            $('#mabed-nav .nav-item').removeClass('active');
            $('#nav-settings').addClass('active');
            api
                .title("Settings")
                .changeContent(view.$el);
            view.render();
        },
        tweets: function () {
            var view = ViewsFactory.tweets();
            $('#mabed-nav .nav-item').removeClass('active');
            $('#nav-tweets').addClass('active');
            api
                .title("Tweets")
                .changeContent(view.$el);
            view.render();
        },
        mabed: function () {  // "Detect events using MABED" tab
            if (api.session_id) {
                var view = ViewsFactory.mabed();
                $('#mabed-nav .nav-item').removeClass('active');
                $('#nav-mabed').addClass('active');
                api
                    .title("Run")
                    .changeContent(view.$el);
                view.render();
            } else {
                var view = ViewsFactory.settings();
                $('#mabed-nav .nav-item').removeClass('active');
                $('#nav-settings').addClass('active');
                api
                    .title("Settings")
                    .changeContent(view.$el);
                view.render();
            }

        },
        results: function (archive) {
            var view = ViewsFactory.client();
            $('#mabed-nav .nav-item').removeClass('active');
            $('#nav-results').addClass('active');
            api
                .title("Results")
                .changeContent(view.$el);
            view.render();
            $('html,body').animate({scrollTop: 0}, 300);

        },
        review: function (archive) {
            var view = ViewsFactory.review();
            $('#mabed-nav .nav-item').removeClass('active');
            $('#nav-events').addClass('active');
            api
                .title("Review")
                .changeContent(view.$el);
            view.render();
            $('html,body').animate({scrollTop: 0}, 300);

        },
        beta: function (archive) {
            var view = ViewsFactory.beta();
            $('#mabed-nav .nav-item').removeClass('active');
            $('#nav-beta').addClass('active');
            api
                .title("Beta")
                .changeContent(view.$el);
            view.render();
            $('html,body').animate({scrollTop: 0}, 300);

        },
        beta2: function (archive) {
            var view = ViewsFactory.beta2();
            $('#mabed-nav .nav-item').removeClass('active');
            $('#nav-beta2').addClass('active');
            api
                .title("Beta2")
                .changeContent(view.$el);
            view.render();
            $('html,body').animate({scrollTop: 0}, 300);

        }
    });

    api.router = new Router();

    return api;

})();
