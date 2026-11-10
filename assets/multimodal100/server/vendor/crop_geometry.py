"""Reject face keypoints inconsistent with the independently tracked pose head."""
import cv2,numpy as np

def filter_points(points,pose):
    n=len(points);raw=[i for i,p in enumerate(points) if p is not None]
    if not raw:raise ValueError('No single-face detection')
    nose=pose[:,0,:2]*1080
    ipd=np.linalg.norm(pose[:,2,:2]-pose[:,5,:2],axis=1)*1080
    reliable=(pose[:,0,3]>=.5)&(ipd>5)&np.isfinite(nose).all(1)
    usable=[i for i in raw if reliable[i]]
    if len(usable)<6:return points,dict(rejected=[],pose_consistency='INSUFFICIENT_RELIABLE_POSE',raw_fraction=len(raw)/n)
    edge=max(5,round(n*.2))
    anchors=[i for i in usable if i<edge or i>=n-edge]
    if len(anchors)<6:anchors=usable
    bias=np.median([points[i][2]-nose[i] for i in anchors],axis=0)
    scale=np.median([np.linalg.norm(points[i][0]-points[i][1])/ipd[i] for i in anchors])
    threshold=max(20.,float(np.median(ipd[anchors]))*.8)
    rejected=[];filtered=list(points);diagnostics=[]
    for i in usable:
        residual=float(np.linalg.norm((points[i][2]-nose[i])-bias))
        ratio=float(np.linalg.norm(points[i][0]-points[i][1])/ipd[i]/scale)
        bad=residual>threshold or not .65<=ratio<=1.5
        diagnostics.append(dict(frame=i,nose_residual_px=residual,relative_eye_scale=ratio))
        if bad:filtered[i]=None;rejected.append(i)
    return filtered,dict(rejected=rejected,pose_consistency='CHECKED',anchor_frames=anchors,nose_bias_px=bias.tolist(),nose_threshold_px=threshold,eye_scale_bounds=[.65,1.5],raw_fraction=len(raw)/n,filtered_fraction=sum(p is not None for p in filtered)/n,diagnostics=diagnostics)

def crops(video,points,reference):
    target=np.vstack([reference[36:42].mean(0),reference[42:48].mean(0),reference[31:36].mean(0),reference[48:68].mean(0)])
    valid=np.array([i for i,p in enumerate(points) if p is not None])
    if len(valid)<2:raise ValueError('Insufficient anchors after geometry filtering')
    pts=np.array([points[i] for i in valid])
    interpolated=np.stack([np.interp(np.arange(len(points)),valid,pts[:,j,k]) for j in range(4) for k in range(2)],1).reshape(-1,4,2)
    result=[];polygons=[]
    for i,frame in enumerate(video):
        margin=min(6,i,len(video)-1-i)
        smooth=interpolated[i-margin:i+margin+1].mean(0)
        smooth+=interpolated[i].mean(0)-smooth.mean(0)
        matrix,_=cv2.estimateAffinePartial2D(smooth,target,method=cv2.LMEDS)
        if matrix is None:raise ValueError('Alignment failed')
        warped=cv2.warpAffine(cv2.cvtColor(frame,cv2.COLOR_RGB2GRAY),matrix,(256,256),flags=cv2.INTER_LINEAR)
        center=smooth[3]@matrix[:,:2].T+matrix[:,2];x,y=np.rint(center).astype(int)
        crop=warped[y-48:y+48,x-48:x+48]
        if crop.shape!=(96,96):raise ValueError('Out-of-frame crop')
        result.append(crop)
        inv=cv2.invertAffineTransform(matrix)
        poly=np.array([[x-48,y-48],[x+48,y-48],[x+48,y+48],[x-48,y+48]],np.float32)
        polygons.append(poly@inv[:,:2].T+inv[:,2])
    return np.stack(result),polygons
