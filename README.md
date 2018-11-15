# weibo-complaint-crawler

Python 3.6+

data source: [微博社区管理中心(Weibo Community Managment Center)](http://service.account.weibo.com/)

crawled complaint report data sample (36,075, up to 2018-08-30):

```mongodb
{ 
    "_id" : ObjectId("5b9b5f0219172c1ee4ec682d"), 
    "url" : "http://service.account.weibo.com/show?rid=K1CaP8wxf7K4j", 
    "title" : "@yvonne爱吃可丽饼 举报@每日上海 不实信息", 
    "reports" : [
        {
            "reporter_url" : "http://weibo.com/u/6154858995", 
            "reporter_name" : "漳州普法", 
            "reporter_img_url" : "https://tvax1.sinaimg.cn/crop.6.8.86.86.50/006Ix9Zhly8fd75vcxu9oj302s02sglq.jpg", 
            "reporter_gender" : "male", 
            "reporter_location" : "福建 漳州", 
            "reporter_description" : "漳州普法官方微博", 
            "report_time" : "2018-08-30 12:47", 
            "report_text" : "漳州普法：#微博辟谣# 不实消息，公安机关已经辟谣！ ."
        }, 
        {
            "reporter_url" : "http://weibo.com/u/2126421215", 
            "reporter_name" : "疯丫头小Ann", 
            "reporter_img_url" : "https://tva3.sinaimg.cn/crop.0.0.640.640.50/7ebe9cdfjw8eg2ht89dz0j20hs0hs74s.jpg", 
            "reporter_gender" : "female", 
            "reporter_location" : "海外 新加坡", 
            "reporter_description" : "酷爱彩妆，护肤！坡县幸福小吃货一枚！", 
            "report_time" : "2018-08-30 12:03", 
            "report_text" : "疯丫头小Ann：#微博辟谣# 有人辟谣了 实际发生地点与人物都和宣传文案不一致 ."
        }, 
        {
            "reporter_url" : "http://weibo.com/u/1433584002", 
            "reporter_name" : "yvonne爱吃可丽饼", 
            "reporter_img_url" : "https://tvax1.sinaimg.cn/crop.0.0.1125.1125.50/5572c182ly8futbpkmiq3j20v90v9acv.jpg", 
            "reporter_gender" : "female", 
            "reporter_location" : "海外 美国", 
            "reporter_description" : "Love is just a word until someone special gives it a meaning.", 
            "report_time" : "2018-08-30 10:57", 
            "report_text" : "yvonne爱吃可丽饼：#微博辟谣# 假信息 ."
        }
    ], 
    "actual_reporter_count" : NumberInt(3), 
    "rumor" : {
        "rumorer_name" : "每日上海", 
        "rumorer_url" : "http://weibo.com/u/2128372947", 
        "rumorer_gender" : "female", 
        "rumorer_location" : "上海", 
        "rumorer_description" : "关注每日上海，乐享潮流资讯。合作联系+Q: 2605326688", 
        "rumor_time" : "2018-08-30 09:58:32", 
        "rumor_url" : "http://weibo.com/2128372947/Gx0aVsVJp", 
        "rumor_text" : "每日上海 ：2018年情人节当天，位于安徽省芜湖广电大厦地下停车场内，42岁女主播与54岁副总编在车内讨论工作，结果由于车内空间狭小，男的太激动，导致突发心梗去世…[doge]"
    }, 
    "official" : {
        "official_text" : "经查，此微博称“位于安徽省芜湖广电大厦地下停车场内，42岁女主播与54岁副总编在车内讨论工作，导致突发心梗去世”不实。@德州运河公安分局 已辟谣：视频中并非芜湖广电大厦地下停车场，且该单位未发生副总编死亡事件 。详情：https://weibo.com/2403912521/Gw7zhxxIm 。被举报人言论构成“发布不实信息”。现根据《微博举报投诉操作细则》（http://service.account.weibo.com/roles/xize ）第19条，对被举报人处理如下：扣除信用积分2分。上述处理在公布后60分钟内生效。"
    }, 
    "looks" : [
        [
            "http://weibo.com/u/5872248592", 
            "simoncV"
        ], 
        [
            "http://weibo.com/u/3221034714", 
            "爱吃肉的牙牙兔"
        ], 
        [
            "http://weibo.com/u/6683056792", 
            "mustard178"
        ], 
        [
            "http://weibo.com/u/2102315083", 
            "_周涵_"
        ], 
        [
            "http://weibo.com/u/5836275950", 
            "决恋星辰98217"
        ], 
        [
            "http://weibo.com/u/1710759290", 
            "independencei989"
        ], 
        [
            "http://weibo.com/u/1347280187", 
            "克服进化论的朱Sir"
        ], 
        [
            "http://weibo.com/u/6554443743", 
            "电影大鸟"
        ], 
        [
            "http://weibo.com/u/6496363207", 
            "Henry_Han_IPR"
        ], 
        [
            "http://weibo.com/u/6075978015", 
            "一个为生活发声的地方"
        ], 
        [
            "http://weibo.com/u/2751779283", 
            "土豪榜叔"
        ], 
        [
            "http://weibo.com/u/6341984206", 
            "诸葛亮亮律师"
        ], 
        [
            "http://weibo.com/u/1578078673", 
            "一脉印象"
        ], 
        [
            "http://weibo.com/u/5649081220", 
            "风乎舞雩_KAZE"
        ], 
        [
            "http://weibo.com/u/6222824749", 
            "起个什么名字好呢-02"
        ], 
        [
            "http://weibo.com/u/5498125999", 
            "即刻"
        ], 
        [
            "http://weibo.com/u/2242945720", 
            "快拉脱离"
        ], 
        [
            "http://weibo.com/u/5850456137", 
            "阳光七星投资集团"
        ], 
        [
            "http://weibo.com/u/2081309513", 
            "1Freekiwi"
        ], 
        [
            "http://weibo.com/u/1742335401", 
            "啊呦喂-嘿"
        ], 
        [
            "http://weibo.com/u/1961261875", 
            "有法依"
        ], 
        [
            "http://weibo.com/u/1447685703", 
            "朝来夕去"
        ], 
        [
            "http://weibo.com/u/1815608542", 
            "严MI"
        ], 
        [
            "http://weibo.com/u/2074743167", 
            "BiuBiuBiu-021"
        ], 
        [
            "http://weibo.com/u/3975175672", 
            "腹肌工场"
        ]
    ]
}
```
