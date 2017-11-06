/*
Adapted from https://github.com/zeroviscosity/d3-js-step-by-step/blob/master/step-5-adding-tooltips.html

MIT License

Copyright (c) 2014-2017 Kent English

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/

(function(d3) {
  'use strict';
  var username = document.getElementById('twitter-username').innerHTML;
  d3.json("/profile/" + username + "/counts.json", function(data) {
    var dataset_followers = [
      { label: 'Female', count: data.followers_counts.female },
      { label: 'Likely female', count: data.followers_counts.mostly_female },
      { label: 'Male', count: data.followers_counts.male },
      { label: 'Likely male', count: data.followers_counts.mostly_male },
      { label: 'Unknown', count: data.followers_counts.unknown },
      { label: 'Ambig/Neutral', count: data.followers_counts.andy },
    ];
    var dataset_following = [
      { label: 'Female', count: data.following_counts.female },
      { label: 'Likely female', count: data.following_counts.mostly_female },
      { label: 'Male', count: data.following_counts.male },
      { label: 'Likely male', count: data.following_counts.mostly_male },
      { label: 'Unknown', count: data.following_counts.unknown },
      { label: 'Ambig/Neutral', count: data.following_counts.andy },
    ];

    var width = 360;
    var height = 360;
    var radius = Math.min(width, height) / 2;
    var donutWidth = 75;
    var legendRectSize = 18;
    var legendSpacing = 4;
    var color = d3.scaleOrdinal(d3.schemeCategory20);


    var svg1 = d3.select('#chart-followers')
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .append('g')
      .attr('transform', 'translate(' + (width / 2) +
        ',' + (height / 2) + ')');
    var arc = d3.arc()
      .innerRadius(radius - donutWidth)
      .outerRadius(radius);
    var pie = d3.pie()
      .value(function(d) { return d.count; })
      .sort(null);
    var tooltip1 = d3.select('#chart-followers')
      .append('div')
      .attr('class', 'tooltip');
    tooltip1.append('div')
      .attr('class', 'label');
    tooltip1.append('div')
      .attr('class', 'count');
    tooltip1.append('div')
      .attr('class', 'percent');
    dataset_followers.forEach(function(d) {
      d.count = +d.count;
    });
    var path1 = svg1.selectAll('path')
      .data(pie(dataset_followers))
      .enter()
      .append('path')
      .attr('d', arc)
      .attr('fill', function(d, i) {
        return color(d.data.label);
      });
    path1.on('mouseover', function(d) {
      var total = d3.sum(dataset_followers.map(function(d) {
        return d.count;
      }));
      var percent = Math.round(1000 * d.data.count / total) / 10;
      tooltip1.select('.label').html(d.data.label);
      tooltip1.select('.count').html(d.data.count);
      tooltip1.select('.percent').html(percent + '%');
      tooltip1.style('display', 'block');
    });
    path1.on('mouseout', function() {
      tooltip1.style('display', 'none');
    });
    var legend1 = svg1.selectAll('.legend')
      .data(color.domain())
      .enter()
      .append('g')
      .attr('class', 'legend')
      .attr('transform', function(d, i) {
        var height = legendRectSize + legendSpacing;
        var offset =  height * color.domain().length / 2;
        var horz = -2 * legendRectSize;
        var vert = i * height - offset;
        return 'translate(' + horz + ',' + vert + ')';
      });
    legend1.append('rect')
      .attr('width', legendRectSize)
      .attr('height', legendRectSize)
      .style('fill', color)
      .style('stroke', color);
    legend1.append('text')
      .attr('x', legendRectSize + legendSpacing)
      .attr('y', legendRectSize - legendSpacing)
      .text(function(d) { return d; });


    var svg2 = d3.select('#chart-following')
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .append('g')
      .attr('transform', 'translate(' + (width / 2) +
        ',' + (height / 2) + ')');
    var arc = d3.arc()
      .innerRadius(radius - donutWidth)
      .outerRadius(radius);
    var pie = d3.pie()
      .value(function(d) { return d.count; })
      .sort(null);
    var tooltip2 = d3.select('#chart-following')
      .append('div')
      .attr('class', 'tooltip');
    tooltip2.append('div')
      .attr('class', 'label');
    tooltip2.append('div')
      .attr('class', 'count');
    tooltip2.append('div')
      .attr('class', 'percent');
    dataset_following.forEach(function(d) {
      d.count = +d.count;
    });
    var path2 = svg2.selectAll('path')
      .data(pie(dataset_following))
      .enter()
      .append('path')
      .attr('d', arc)
      .attr('fill', function(d, i) {
        return color(d.data.label);
      });
    path2.on('mouseover', function(d) {
      var total = d3.sum(dataset_following.map(function(d) {
        return d.count;
      }));
      var percent = Math.round(1000 * d.data.count / total) / 10;
      tooltip2.select('.label').html(d.data.label);
      tooltip2.select('.count').html(d.data.count);
      tooltip2.select('.percent').html(percent + '%');
      tooltip2.style('display', 'block');
    });
    path2.on('mouseout', function() {
      tooltip2.style('display', 'none');
    });
    var legend2 = svg2.selectAll('.legend')
      .data(color.domain())
      .enter()
      .append('g')
      .attr('class', 'legend')
      .attr('transform', function(d, i) {
        var height = legendRectSize + legendSpacing;
        var offset =  height * color.domain().length / 2;
        var horz = -2 * legendRectSize;
        var vert = i * height - offset;
        return 'translate(' + horz + ',' + vert + ')';
      });
    legend2.append('rect')
      .attr('width', legendRectSize)
      .attr('height', legendRectSize)
      .style('fill', color)
      .style('stroke', color);
    legend2.append('text')
      .attr('x', legendRectSize + legendSpacing)
      .attr('y', legendRectSize - legendSpacing)
      .text(function(d) { return d; });


  });
})(window.d3);
