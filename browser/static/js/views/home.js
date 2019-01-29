app.views.home = Backbone.View.extend({
    template: _.template($("#tpl-page-1").html()),
    initialize: function() {
        this.render();
        var handler = _.bind(this.render, this);
    },
    render: function(){
        var html = this.template();
        this.$el.html(html);
        this.delegateEvents();
        jarallax(document.querySelectorAll('.jarallax'));

        jarallax(document.querySelectorAll('.jarallax-keep-img'), {
            keepImg: true,
        });
        return this;
    }
});
