from pydantic import BaseModel


class AnnouncementsModuleStatus(BaseModel):
    module: str
    status: str
    next_slice: str


class AnnouncementHeroMetric(BaseModel):
    label: str
    value: str


class AnnouncementSnapshotItem(BaseModel):
    label: str
    value: str


class AnnouncementSnapshot(BaseModel):
    title: str
    items: list[AnnouncementSnapshotItem]


class AnnouncementsDashboardResponse(BaseModel):
    module: str
    status: str
    kicker: str
    title: str
    description: str
    metrics: list[AnnouncementHeroMetric]
    snapshots: list[AnnouncementSnapshot]
    notes_title: str
    notes_body: str
    footer_note: str
