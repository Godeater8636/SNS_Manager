from pydantic import BaseModel


class DailyDataPoint(BaseModel):
    date: str
    impressions: int
    link_clicks: int
    likes: int
    retweets: int


class TopPost(BaseModel):
    post_id: str
    content: str
    impressions: int
    engagement_rate: float


class TopLink(BaseModel):
    link_id: str
    name: str
    clicks: int


class DashboardSummary(BaseModel):
    total_impressions: int
    total_likes: int
    total_retweets: int
    total_link_clicks: int
    avg_engagement_rate: float


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    top_posts: list[TopPost]
    top_links: list[TopLink]
    daily_series: list[DailyDataPoint]
